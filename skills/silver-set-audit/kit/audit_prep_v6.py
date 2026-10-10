"""Render one v6 run root into audit-ready files.

    python audit_prep_v6.py RUN_ROOT OUT_DIR [--parent PARENT_RUN_ROOT] [--slice-size 24]

Writes OUT_DIR/sets.md (every approved set: header, SIMILARITY, plan facts incl.
the S manner plan, five prompts), OUT_DIR/pairs.tsv, OUT_DIR/funnel.json, and
OUT_DIR/slices/slice_N.md. For a style-refresh run root pass --parent with the
v5 forward run root so the language column can be filled from its sampling.
"""
import argparse, collections, csv, difflib, json, pathlib

ap = argparse.ArgumentParser()
ap.add_argument("run_root"); ap.add_argument("out_dir")
ap.add_argument("--parent", default=None); ap.add_argument("--slice-size", type=int, default=24)
args = ap.parse_args()
R = pathlib.Path(args.run_root); OUT = pathlib.Path(args.out_dir); OUT.mkdir(parents=True, exist_ok=True)
P = pathlib.Path(args.parent) if args.parent else None

def jl(root, p):
    p = root / p
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []
def js(root, p):
    p = root / p
    return json.load(open(p)) if p.exists() else {}

approved = jl(R, "variants/final/approved_contrast_sets.jsonl")
excluded = jl(R, "variants/final/excluded_contrast_sets.jsonl")
vman = js(R, "variants/final/manifest.json")
sampled = jl(R, "sampling/sampled_turns.jsonl") or (jl(P, "sampling/sampled_turns.jsonl") if P else [])
by_sha = {s["source_prompt_sha256"]: s for s in sampled if "source_prompt_sha256" in s}

exc_c = collections.Counter((e.get("classified_anchor_role"), e.get("status") or e.get("final_status")) for e in excluded)
ap_c = collections.Counter((a["anchor_role"], a["behavior_family"]) for a in approved)
funnel = {
    "run_root": str(R), "pipeline_version": (vman.get("policy") or {}).get("pipeline_version"),
    "approved": len(approved), "excluded": len(excluded),
    "approved_native_h": sum(1 for a in approved if a.get("native_h")),
    "approved_by_role_family": {f"{k[0]}|{k[1]}": v for k, v in ap_c.items()},
    "excluded_by_role_status": {f"{k[0]}|{k[1]}": v for k, v in exc_c.items()},
    "human_verify_required": sum(1 for a in approved if (a.get("construction") or {}).get("human_verify_required") or a.get("human_verify_required")),
    "repair_rounds": collections.Counter(str((a.get("construction") or {}).get("repair_rounds")) for a in approved),
    "variants_manifest_counts": vman.get("counts"),
}
json.dump(funnel, open(OUT / "funnel.json", "w"), indent=1, ensure_ascii=False)

ROLES = ["misaligned_target", "aligned_control", "hard_negative", "style_control", "paraphrase_target"]
LETTER = {"misaligned_target": "T", "aligned_control": "A", "hard_negative": "H", "style_control": "S", "paraphrase_target": "P"}
DIMS = ["address_politeness", "register_formality", "sentence_shape", "orthography_punctuation", "discourse_format"]
def sim(a, b): return difflib.SequenceMatcher(None, a, b).ratio()
def prompt_of(role):
    if "user_prompt" in role: return role["user_prompt"]
    msgs = role.get("rendered_messages") or []
    return "\n".join(m.get("content", "") for m in msgs if m.get("role", "user") == "user")

blocks = []
with open(OUT / "pairs.tsv", "w") as tsv:
    tsv.write("candidate_id\tfamily\tanchor\t" + "\t".join(f"{LETTER[a]}-{LETTER[b]}" for i, a in enumerate(ROLES) for b in ROLES[i + 1:]) + "\tlen_T\ts_jaccard\n")
    for a in sorted(approved, key=lambda x: (x["behavior_family"], x["candidate_id"])):
        roles = a["complete_contrast"]["roles"]; pr = {r: prompt_of(roles[r]) for r in ROLES}
        plan = a.get("plan") or {}; rc = plan.get("role_contracts") or {}
        hn = rc.get("hard_negative") or {}; sc = rc.get("style_control") or {}
        src = by_sha.get(a.get("source_prompt_sha256"), {})
        pairs = {f"{LETTER[x]}-{LETTER[y]}": sim(pr[x], pr[y]) for i, x in enumerate(ROLES) for y in ROLES[i + 1:]}
        sj = ((a.get("cue_retention") or {}).get("style_content_word_jaccard_to_target"))
        con = a.get("construction") or {}
        out = [f"\n\n## {a['candidate_id']}  anchor={a['anchor_role']} classified={a.get('classified_anchor_role')} native_h={a.get('native_h')} contract_source={a.get('behavior_contract_source')} turn_index={a.get('source_turn_index')} lang={src.get('language') or src.get('lang')} repair_rounds={con.get('repair_rounds')} human_verify={bool(con.get('human_verify_required') or a.get('human_verify_required'))}"]
        out.append("SIMILARITY(char ratio): " + " ".join(f"{k}={v:.2f}" for k, v in pairs.items()) + f" len_T={len(pr['misaligned_target'])}")
        out.append(f"MECHANISM: {a.get('behavior_mechanism')}")
        out.append(f"PLAN.decision_target_mode={plan.get('target_mode')}")
        out.append(f"PLAN.H.surface_action: {hn.get('surface_action')}")
        out.append(f"PLAN.H.original_fact: {hn.get('original_fact_in_target')}")
        out.append(f"PLAN.H.decisive_fact: {hn.get('decisive_fact')}")
        ds = sc.get("domain_selection") or {}
        dt = sc.get("disjoint_task") or {}
        out.append(f"PLAN.S.domain: {json.dumps(ds, ensure_ascii=False)[:400]}")
        out.append(f"PLAN.S.task: {dt.get('task_summary')} | deliverable: {dt.get('required_deliverable')}")
        out.append(f"PLAN.S.disjointness: {dt.get('disjointness_argument')}")
        md = sc.get("manner_dimensions") or {}
        for d in DIMS:
            e = md.get(d) or {}
            out.append(f"PLAN.S.manner_dimensions.{d}: status={e.get('status')} quote_T={json.dumps(e.get('quote'), ensure_ascii=False)} note={e.get('note')}")
        out.append(f"S_JACCARD(content words S vs T): {sj}")
        for r in ROLES:
            out.append(f"\n[{r}]{' (ANCHOR)' if roles[r].get('is_anchor') else ''}\n{pr[r]}")
        blocks.append("\n".join(out))
        tsv.write(f"{a['candidate_id']}\t{a['behavior_family']}\t{a['anchor_role']}\t" + "\t".join(f"{v:.2f}" for v in pairs.values()) + f"\t{len(pr['misaligned_target'])}\t{sj}\n")

(OUT / "sets.md").write_text("".join(blocks))
sl = OUT / "slices"; sl.mkdir(exist_ok=True)
for i in range(0, len(blocks), args.slice_size):
    (sl / f"slice_{i // args.slice_size + 1}.md").write_text("".join(blocks[i:i + args.slice_size]))
print(json.dumps({"approved": len(approved), "excluded": len(excluded), "slices": (len(blocks) + args.slice_size - 1) // args.slice_size, "human_verify_required": funnel["human_verify_required"]}, ensure_ascii=False))
