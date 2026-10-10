# Audit kit for v6 contrast sets

Batch preparation for the same construction audit used by both installed skills.
Use [the shared rubric](../codex/audit-contrast-set/rubric_v6.md); the Claude copy
is identical. The kit does not contain a separate rubric.

| File | What |
|---|---|
| `slice_auditor_prompt_v6.md` | Per-slice wrapper. Fill `{RUBRIC_PATH}`, `{SLICE_PATH}`, `{OUT_PATH}`, `{N}`. |
| `audit_eval.py` | Prepare, optionally run audits through the signed-in Claude CLI, freeze predictions, and score agreement/kappa. |
| `audit_prep_v6.py` | Renders a run root into `sets.md`, `pairs.tsv`, `funnel.json` and `slices/slice_N.md` (24 sets each). |

## Run

From the repository root, with explicit run and output paths:

```bash
python3 kit/audit_prep_v6.py /path/to/run /path/to/audit/prep
```

For style-refresh runs without `sampling/`, pass `--parent /path/to/parent/run`
to fill the language field. Preparation reads source runs and writes the requested
output directory; it does not call a model. Paid model audits require explicit
authorization.

For each slice, provide the wrapper with all placeholders filled. Set
`RUBRIC_PATH` to either installed skill's current `rubric_v6.md`. Collect one v4
JSONL verdict per source id, including unresolved records as deny with evidence-gap explanations. Validate each
record with the skill helper before importing or aggregating it.

## Decisions and historical comparisons

Use only `decision: approve|deny`; do not emit a separate verdict category.
Approve includes minor revision needs when all defining role relations still
hold. Deny for a failed defining relation, an ineligible set, or insufficient
material evidence; explain which applies.
Use `revision_needed` for repair instructions and `evidence_gap` for uncertainty;
a denial with an explained gap may keep unassessable H/S findings null. Do not
convert missing evidence into a demonstrated semantic defect. Behaviour labels
remain out of scope. Exclude generic persona-template transcripts with an
interchangeable tail request under the rubric; task-specific roleplay and ordinary
conversation data are not automatically excluded. Deny when A/H retain active
harmful permissions that the contrast does not neutralize. Duplicate removal is outside
the skill: do not retrieve reference collections or deny for duplication.
Historical v1/v2/v3 records are preserved without rewriting.
The approval rate counts approve only, and status separates new binary decisions
from historical verdicts. Freeze skill v0.10.1 with predictions because the v4
record shape does not identify the acceptance policy. Score human approve + revise
as approve and reject as deny; report disputed/unsure separately from the resolved
agreement denominator. Review-app v4 import compatibility remains unverified.

## Evidence in slices

Slices contain original prompt text, anchor metadata, and H/S planner diagnostics.
They omit family labels and family-selection rationale. `pairs.tsv` and
`funnel.json` retain family metadata for provenance; they are not audit inputs.
Plans and similarity/Jaccard scores are diagnostic claims, never verdict thresholds.
Verify all five roles, even in runs that regenerated only S.

These run slices include construction metadata and are not a blinded evaluation
packet. For an independent performance test, follow the skill's separate protocol
for prompt-only inputs and saving predictions before joining human labels.


## Reproducible DEV / blind evaluation

`audit_eval.py` uses Python's standard library. Its `run` command invokes the
official Claude CLI using your signed-in Claude subscription; it needs no SDK or
API key. Prepare, validate, freeze, and score remain offline. It supports the
bundle's `dev` and `blind` collections and uses `primary_decision` only at scoring.
You can also retain the manual Claude-session workflow below.

### 1. Prepare a new run

From this repository root:

```bash
python3 kit/audit_eval.py prepare --bundle /absolute/path/harley-v6-audit-bundle.json --split dev --sample-size 95 --seed 42 --batch-size 12 --model claude-opus-5 --settings "effort=high" --run /absolute/path/new-dev-run
```

Provide `--settings` to document the planned settings. For automated runs, the
runner additionally records the CLI version, actual effort setting and returned
model usage, and rejects responses reporting another model. Pin a full model id
for repeatability; the `opus` alias is allowed but can change over time. Use `--skill PATH` for
another installed skill; the default is this repository's Claude copy.

For a full blind run, use `--split blind` and omit `--sample-size`. Exclusions are
never automatic: repeat `--exclude-id ID` for each explicit exclusion. The order
is **sort IDs, sample, then exclude without replacement**, preserving our DEV
protocol. Unknown exclusions fail, while exclusions outside the drawn sample are
reported. `--disputed credit` is the default; `--disputed exclude` is also supported.
The choice is saved before judgments are made. Existing run directories are never
reused or overwritten.

### 2. Run automatically through your subscription

Install the [official Claude CLI](https://code.claude.com/docs/en/setup), then run
`claude auth login` and choose your Claude subscription account. The runner can
find `~/.local/bin/claude` even if that directory is absent from PATH; override
with `--claude-bin /absolute/path/claude` if necessary.

```bash
python3 kit/audit_eval.py check-cli
python3 kit/audit_eval.py run --run /absolute/path/new-dev-run --workers 4 --effort high
```

The `run` command is the only step that consumes model quota. It runs up to four
independent batches concurrently by default (configurable 1–8), saves their output,
freezes predictions, and scores locally. Opus receives the frozen skill/rubric and
only its assigned prompt-only records via stdin. It neither orchestrates the run
nor reads the answer key. Every call starts a fresh session in an isolated temp
directory, with built-in and MCP tools disabled, no session persistence, and
`--safe-mode` to suppress user/project customizations and memory. Managed policy
still applies. We use safe mode rather than `--bare`, which disables subscription
login. See [CLI reference](https://code.claude.com/docs/en/cli-reference) and
[authentication](https://code.claude.com/docs/en/authentication).

The child process also disables the CLI's background session-title model request
with `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1`; see the
[environment variable reference](https://code.claude.com/docs/en/env-vars).
An inherited effort override is removed so `--effort` controls the run.

API keys, alternate provider overrides, and token overrides are removed from the
child environment only. The runner checks for a first-party `claude.ai` login;
it does not read/export tokens or fall back to API billing. Account quotas and
any subscription extra-usage settings still apply. The first-party CLI handles
authentication itself. `check-cli` makes no model request and prints no email or
organization identifiers.

Use `--cli-model claude-opus-5` when an older prepared manifest names the model
as `Claude Opus 5`. `--timeout 600` sets the per-batch deadline. CLI settings are
saved before calls. Wrong/missing model metadata, timeouts, refusals, malformed
JSON, duplicate ids, and incomplete batch output are logged as operational failures,
never denials. An invalid batch is conservatively recorded as failed for all its
assigned ids; raw output remains available for inspection. There is no automatic
resubmission by the harness; the CLI may retry transient transport failures.

`cli_logs/` stores raw responses and per-batch metadata. `cli_run.json` stores
execution settings and the runner hash. Their hashes are included in the frozen
snapshot. A normal completed run cannot be rerun or overwritten. Interrupted runs
can resume only whole batches that have no existing logs/results, with exactly
the same runner settings. A partial batch, orphaned logs, or stale `.cli_running`
lock stops for inspection rather than silently spending quota again. Failed
records are not automatically retried. Do not remove locks while a runner is live.

If all model calls fail, the run still produces a coverage/failure report with
undefined agreement; success of the script alone does not mean the audit succeeded.

### Manual alternative: audit in Claude

Start a fresh session and ask it to follow the generated `RUN.md`. It contains the
exact paths/commands. Reviewers receive only `reviewer/INSTRUCTIONS.md`, their
assigned `reviewer/batches/*.jsonl`, and the frozen `reviewer/skill/` files.
The coordinator does not need to open the source bundle. No source prompts are
printed by prepare, and no judgment-bearing metadata enters the reviewer files.

Each batch writes a separate JSONL file into `results/`, using this compact
**evaluation output** schema (distinct from the full skill recording schema):

```json
{"candidate_id":"id","decision":"approve","reason":"Evidence-based reason.","tags":[]}
```

For a refusal, parsing failure, or other operational blocker, write instead:

```json
{"candidate_id":"id","operational_error":"Specific explanation."}
```

Keep one entry per selected ID across all batches. Neither failures nor missing
outputs are automatically converted to semantic denials. To resume interrupted
work, `validate` lists missing IDs; preserve completed predictions. Do not rewrite
results after exposure to labels.

### 3. Validate, freeze, and score

```bash
python3 kit/audit_eval.py validate --run /absolute/path/new-dev-run
python3 kit/audit_eval.py freeze --run /absolute/path/new-dev-run
python3 kit/audit_eval.py score --run /absolute/path/new-dev-run
```

`validate` reports readiness and missing IDs; malformed/duplicate/unexpected
records fail. `freeze` requires every selected ID to have a prediction or explicit
operational failure. It snapshots results and hashes the manifest; the prepared
skill and batch hashes are verified. `score` refuses to run before freeze, verifies
frozen content and the exact source-bundle hash, and scores only the snapshot.
A source moved to another location can be supplied with `score --bundle PATH`;
its bytes must still match. Source edits require a new run. Previously generated
reports cannot be overwritten. Files are marked read-only where appropriate,
but hashes and permissions are workflow checks, not an adversarial security boundary
or proof that a model never saw answers elsewhere.

### Reports

- `comparison_report.md`: coverage, adjusted agreement, confusion matrix, kappa,
  disagreements, and operational failures.
- `comparison_report.json`: exact counts, every comparison, source hashes, and
  post-freeze human review notes for disagreements.
- Human approve + revise map to approve; reject maps to deny. Unsure is excluded.
- With disputed credit, either **actual prediction** gets credit. A failure does
  not earn disputed credit. Cohen's kappa always uses resolved predicted cases.
- Operational failures reduce scored coverage, not the selected-set count. Reports
  also show correct predictions / all selected scorable cases so missing results
  cannot be hidden behind a high completed-case agreement rate. Kappa is undefined
  when the denominator or its chance-adjustment term is zero.
- Duplicate-related human rejections remain in the score. A reviewer can interpret
  their notes after scoring; the script does not guess semantic disagreement types.
- Sampled/excluded runs are labeled reduced evaluations. Repeated DEV tuning does
  not establish untouched-test accuracy. Do not tune against TEST outcomes.

Automated tests use synthetic data and mocked CLI responses; they make no model calls:

```bash
python3 -B -m unittest discover -s kit -p 'test_*.py'
```
