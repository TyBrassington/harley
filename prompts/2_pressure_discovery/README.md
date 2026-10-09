# Pressure-discovery prompts

Every call used GPT-6 Astra (`gpt-6-astra`) through Codex CLI 0.154.0
(`codex exec`). Tools, web search, plugins and user configuration were turned
off, and the sandbox was read-only. Each answer had to follow the matching file
in [`schemas/`](schemas/).

The templates have no `{placeholders}`. Each file ends with an `INPUT_JSON`
line, and the call's JSON input follows that line. The input was serialized with
`json.dumps(payload, ensure_ascii=False, sort_keys=True)`:

- part b also used `indent=2`;
- `add_features.txt` and part c used compact separators `(",", ":")`.

Every file here is a byte-for-byte prefix of the archived prompt of every call
in its stage.

## a. Features (118, then 4 added)

| File | Step | Effort | Calls | Input | SHA-256 (first 16) |
|---|---|---|---|---|---|
| `describe.txt` | Describe the pressures in the discovery sets | high | 12 | 10 sets per call, each prompt with its condition | `08ea3ec0b881394e` |
| `name_candidates.txt` | Propose candidate features | high | 12 | The same sets with conditions removed, plus their descriptions | `ebcd6f6a4df3acdb` |
| `merge_plan.txt` | Group candidates into features (draft, then refinement) | high | 2 | Candidates; the refinement call also gets the calibration labels | `904d07fafb9bb902` |
| `write_feature.txt` | Write one feature card per group | high | 234 (116 draft, 118 refined) | The group, the other groups, its candidates and their source sets | `9de072740866b59d` |
| `label_set.txt` | Label a whole set with the codebook | high | 280 (40 calibration, 200 final, 40 repeat), plus 8 retries | Five prompts with conditions removed, plus the codebook | `b915f9474ded0b8e` |
| `label_prompt.txt` | Label one prompt (calibration only) | high | 200 | One prompt, plus the codebook | `1e7c43926749549b` |
| `add_features.txt` | Add features for the sets that had none | high | 1 | Those sets and the hierarchy cards | `c5ee6fd53f11b1f1` |

[`inputs/codebook_118.json`](inputs/codebook_118.json) is the frozen codebook,
byte-identical to the one inside every final and repeat `label_set` call. Only
six fields reach the model: `feature_id`, `name`, `definition`, `inclusion`,
`exclusion` and `nearest_distinction`.

[`inputs/added_features_119_122.json`](inputs/added_features_119_122.json) holds
the four added features in the same fields. UF121 was reworded after the
model call, without another call. The file gives the wording the paper's
hierarchy uses.

## b. Families, classes and domains

| File | Step | Effort | Calls | Input | SHA-256 (first 16) |
|---|---|---|---|---|---|
| `propose_families.txt` | Two independent family proposals | high | 2 | The 118 feature cards | `8286086616e1bff5` |
| `reconcile_families.txt` | Settle features the two proposals grouped differently | high | 1 | Both proposals, the disputed features and their cards | `02e29babe9aea024` |
| `document_families.txt` | Write the 83 family cards | high | 4 | Families and their feature cards | `557c29816e031d0a` |
| `audit_families.txt` | Audit the family cards | high | 1 | Family cards, proposals, disagreements | `d56e7d614510051b` |
| `propose_classes.txt` | Group families into classes (about 15 asked for, 12 to 18 accepted) | high | 1 | The 83 family cards | `4e273d21f788898c` |
| `propose_domains.txt` | Group classes into domains | high | 1 | The class cards | `d982b3e37dcabd2f` |

## c. Class assignment

| File | Step | Effort | Calls | Input | SHA-256 (first 16) |
|---|---|---|---|---|---|
| `assign_classes.txt` | Assign each set to classes | medium | 200 | [`inputs/class_taxonomy.json`](inputs/class_taxonomy.json) and one set, with its five prompts labelled T/A/H/S/P | `f324a51c8fa4a79b` |

This stage ran at medium effort. Unlike the labelling in part a, it saw each
prompt's condition.

In `class_taxonomy.json`:

- `pressure_families` holds the 16 class cards (IDs `PC_…`);
- `broad_domains` holds the 6 domain cards;
- `family_to_domain` maps classes to domains.

The cards include five field edits that people made after the model wrote
them.

The paper's 12 classes come from the 16 by merging three classes into others
after assignment, with no model call. A class with no sets drops out. See
[`inputs/class_merge_16_to_12.json`](inputs/class_merge_16_to_12.json).

## Not included

These were left out:

- the single-call merge template of part a, whose two calls returned no
  answer, and its refinement template, which was never sent;
- two hierarchy templates that no completed call used;
- failed attempts that used earlier templates;
- diagnostic audits that produced no labels.
