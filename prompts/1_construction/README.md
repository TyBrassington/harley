# Construction prompts

These are the eight prompts of construction pipeline v6, numbered in the order
the pipeline calls them. Each is a system prompt. The material a stage works on
is substituted at its placeholders as JSON. Each prompt's output schema has the
same name in [`inputs/schemas/`](inputs/schemas/). The last column but one gives
the original prompt and schema names, as recorded in each run's
`pipeline_version.json`.

| File | Stage | Model | Setting | Placeholders | Original names | SHA-256 (first 16) |
|---|---|---|---|---|---|---|
| [`1_screen_recall.txt`](1_screen_recall.txt) | Recall screen | `gemini-3.8-flash` | Vertex batch, thinking high | `{behavior_taxonomy}` `{candidate_payload}` | `screen_recall_v3.txt`, `screen-recall-v3` | `e2e5065fffa515e1` |
| [`2_screen_precision.txt`](2_screen_precision.txt) | Precision screen | `gemini-3.8-flash` | Vertex batch, thinking high | `{behavior_taxonomy}` `{candidate_payload}` | `screen_precision_v3.txt`, `screen-precision-v2` | `531aa8c3028d2037` |
| [`3_evidence_extraction.txt`](3_evidence_extraction.txt) | Evidence extraction | `gpt-5.6-sol` | Codex CLI, reasoning xhigh | `{behavior_taxonomy}` `{candidate_payload}` | `stage1_evidence_extraction_v1.txt`, `evidence-extraction` | `97a9d3ff4101ded3` |
| [`4_role_classification.txt`](4_role_classification.txt) | Anchor-role classification | `gpt-5.6-sol` | Codex CLI, reasoning xhigh | `{behavior_taxonomy}` `{candidate_payload}` `{analysis_payload}` | `stage2_role_classification_v3.txt`, `role-classification-v3` | `5d7d6d7764d40a24` |
| [`5_variant_plan.txt`](5_variant_plan.txt) | Variant plan | `gpt-5.6-sol` | Codex CLI, reasoning xhigh | `{behavior_taxonomy}` `{candidate_payload}` `{variant_contract}` | `variant_plan_v5.txt`, `variant-plan-v5` | `156ea7f8cfc9d768` |
| [`6_variant_writer.txt`](6_variant_writer.txt) | Variant writer | `gemini-3.8-flash` | Vertex batch, thinking high | `{candidate_payload}` | `variant_writer_v5.txt`, `variant-writer-v3` | `43288d99cb137470` |
| [`7_variant_review.txt`](7_variant_review.txt) | Review and recheck | `gpt-5.6-sol` | Codex CLI, reasoning xhigh; two blind passes | `{candidate_payload}` | `variant_review_v5.txt`, `variant-review-v4` | `9f6fe0f287623ae2` |
| [`8_variant_repair.txt`](8_variant_repair.txt) | Variant repair | `gemini-3.8-flash` | Vertex batch, thinking high | `{candidate_payload}` | `variant_repair_v4.txt`, `variant-repair-v3` | `9dbf8e93afa25e13` |

The review prompt is also used for the recheck after repair. A writer bundle
that came back truncated or failed its schema was retried for up to three more
rounds.

## Inputs

| Placeholder or file | What fills it |
|---|---|
| `{behavior_taxonomy}` in prompts 1–4 | A JSON list built from [`inputs/behavior_taxonomy.json`](inputs/behavior_taxonomy.json). Each of the ten families keeps `name`, `definition`, `target_behavior_signal`, `not_examples` and `boundary_note`, serialized with an indent of 2. |
| `{behavior_taxonomy}` in prompt 5 | The same taxonomy, given as the full entry for the anchor's family. When the planner chooses the family itself, the entries for all ten families are given. |
| `{variant_contract}` | [`inputs/variant_contract.json`](inputs/variant_contract.json), as canonical JSON. |
| `{candidate_payload}` | Per-item JSON: the anchor turn plus the fields that stage needs. Retrieval provenance is never included. |
| `{analysis_payload}` | The evidence-extraction output for the same turn. |
| [`inputs/style_domain_pool.json`](inputs/style_domain_pool.json) | The task domains offered to the planner for the style control. They reach the plan prompt as `offered_domains` inside `{candidate_payload}`. |
| [`inputs/schemas/`](inputs/schemas/) | The JSON schema each stage's output was validated against. Gemini batch requests received a Vertex-compatible projection of the same schema. |

| Input file | Original name | SHA-256 (first 16) |
|---|---|---|
| `behavior_taxonomy.json` | `behavior_family_taxonomy.v2_10families.snapshot.json` | `f5486fc60fb4a3a7` |
| `variant_contract.json` | `variant_construction_contract_v5.json` | `efae6e9bef7ea5da` |
| `style_domain_pool.json` | `style_domain_pool_v1.json` | `38da25764e46c16a` |
