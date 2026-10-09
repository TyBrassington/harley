# Construction prompts

These are the eight prompts of construction pipeline v6, in the order the
pipeline calls them. Each is a system prompt. The material a stage works on is
substituted at its placeholders as JSON. File names are the ones recorded in
each run's `pipeline_version.json`.

| # | File | Stage | Model | Setting | Placeholders | Output schema | SHA-256 (first 16) |
|---|---|---|---|---|---|---|---|
| 1 | `screen_recall_v3.txt` | Recall screen | `gemini-3.8-flash` | Vertex batch, thinking high | `{behavior_taxonomy}` `{candidate_payload}` | `screen-recall-v3` | `e2e5065fffa515e1` |
| 2 | `screen_precision_v3.txt` | Precision screen | `gemini-3.8-flash` | Vertex batch, thinking high | `{behavior_taxonomy}` `{candidate_payload}` | `screen-precision-v2` | `531aa8c3028d2037` |
| 3 | `stage1_evidence_extraction_v1.txt` | Evidence extraction | `gpt-5.6-sol` | Codex CLI, reasoning xhigh | `{behavior_taxonomy}` `{candidate_payload}` | `evidence-extraction` | `97a9d3ff4101ded3` |
| 4 | `stage2_role_classification_v3.txt` | Anchor-role classification | `gpt-5.6-sol` | Codex CLI, reasoning xhigh | `{behavior_taxonomy}` `{candidate_payload}` `{analysis_payload}` | `role-classification-v3` | `5d7d6d7764d40a24` |
| 5 | `variant_plan_v5.txt` | Variant plan | `gpt-5.6-sol` | Codex CLI, reasoning xhigh | `{behavior_taxonomy}` `{candidate_payload}` `{variant_contract}` | `variant-plan-v5` | `156ea7f8cfc9d768` |
| 6 | `variant_writer_v5.txt` | Variant writer | `gemini-3.8-flash` | Vertex batch, thinking high | `{candidate_payload}` | `variant-writer-v3` | `43288d99cb137470` |
| 7 | `variant_review_v5.txt` | Review and recheck | `gpt-5.6-sol` | Codex CLI, reasoning xhigh; two blind passes | `{candidate_payload}` | `variant-review-v4` | `9f6fe0f287623ae2` |
| 8 | `variant_repair_v4.txt` | Variant repair | `gemini-3.8-flash` | Vertex batch, thinking high | `{candidate_payload}` | `variant-repair-v3` | `9dbf8e93afa25e13` |

The review prompt is also used for the recheck after repair. A writer bundle
that came back truncated or failed its schema was retried for up to three more
rounds.

## Inputs

| Placeholder or file | What fills it |
|---|---|
| `{behavior_taxonomy}` in prompts 1–4 | A JSON list built from [`inputs/behavior_family_taxonomy.json`](inputs/behavior_family_taxonomy.json). Each of the ten families keeps `name`, `definition`, `target_behavior_signal`, `not_examples` and `boundary_note`, serialized with an indent of 2. |
| `{behavior_taxonomy}` in prompt 5 | The same taxonomy, given as the full entry for the anchor's family. When the planner chooses the family itself, the entries for all ten families are given. |
| `{variant_contract}` | [`inputs/variant_construction_contract_v5.json`](inputs/variant_construction_contract_v5.json), as canonical JSON. |
| `{candidate_payload}` | Per-item JSON: the anchor turn plus the fields that stage needs. Retrieval provenance is never included. |
| `{analysis_payload}` | The evidence-extraction output for the same turn. |
| [`inputs/style_domain_pool_v1.json`](inputs/style_domain_pool_v1.json) | The task domains offered to the planner for the style control. They reach the plan prompt as `offered_domains` inside `{candidate_payload}`. |
| [`inputs/schemas/`](inputs/schemas/) | The JSON schema each stage's output was validated against. Gemini batch requests received a Vertex-compatible projection of the same schema. |

| Input file | SHA-256 (first 16) |
|---|---|
| `behavior_family_taxonomy.json` | `f5486fc60fb4a3a7` |
| `variant_construction_contract_v5.json` | `efae6e9bef7ea5da` |
| `style_domain_pool_v1.json` | `38da25764e46c16a` |
