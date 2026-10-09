# Behaviour-discovery prompts

These prompts built the 57-behaviour codebook and labelled the flagged responses
with it. They also aligned the two independent discovery runs.

**How each call was made**
- Model: Claude Opus 5.5 (`claude-opus-5-5`), effort `high`.
- Each call was a fresh headless `claude -p` process. The main run used Claude Code 2.1.280 and 2.1.281; the GLM-5.3-Flash add-on used 2.1.284.
- Tools, settings files, MCP servers and slash commands were disabled.
- Calls ran in an empty working directory with a minimal environment:

```
cd /tmp/harley_call_cwd && <filled USER template on stdin> | env -i PATH HOME USER LOGNAME LANG TMPDIR SHELL TERM \
  claude -p --model claude-opus-5-5 --effort high --system-prompt "<SYSTEM section>" \
  --output-format json --tools "" --max-turns 1 --setting-sources "" --strict-mcp-config \
  --disable-slash-commands --no-session-persistence
```

Temperature and other sampling parameters cannot be set in headless mode, so
they were left at the defaults.

## How a template becomes a call

**Splitting the file.** Each `.md` file has a `## SYSTEM` section and a `## USER`
section. The code splits the file with:

```
^## SYSTEM\s*\n(.*?)\n## USER\s*\n(.*)$   (re.S | re.M)
```

It then strips both parts:
- the stripped SYSTEM text is the system prompt, used verbatim;
- the stripped USER text is the template sent on stdin.

The title line above `## SYSTEM` is never sent.

**Filling placeholders.** Placeholders are written `{{NAME}}` and filled in one
pass. Inside a filled value, a closing tag that matches one of the template's
wrappers (for example `</response>`) has its `<` replaced with `&lt;`. Nothing
else is changed.

**Blinding.** The model never sees the system name, condition, language,
pressure class, judge label, set id or response id. Merge stages use opaque
random item ids.

**Checks and retries**
- Every answer had to be a JSON object in the form its prompt specifies.
- An invalid answer was retried once with identical input.
- A refusal was retried once alone. If it was still refused, it was logged as
  `refused_final` and sent to the fallback below.

## Fallback for refusals: GPT-5.6 Sol

When Claude's answer ended `refused_final`, the same template was sent to
GPT-5.6 Sol (`gpt-5.6-sol`, reasoning effort `high`). It went through the Codex
CLI bundled with the ChatGPT app (`codex exec`; 0.154.0-alpha.6.2 when the
fallback was set up), with tools, web search and user configuration turned
off, and a read-only sandbox in an empty directory.

Codex takes one message, so stdin was:

```
<sol_fallback_preamble.txt> + <SYSTEM section> + "\n\n" + <filled USER template>
```

[`sol_fallback_preamble.txt`](sol_fallback_preamble.txt) is that preamble,
byte for byte (135 bytes, ending in two newlines). Claude's refused calls stay
in the logs; fallback answers are stored separately with
`annotator = gpt-5.6-sol`.

## Prompts

| File | Step | Claude Opus 5.5 calls | GPT-5.6 Sol fallback calls | Placeholders | SHA-256 (first 16) |
|---|---|---|---|---|---|
| `describe_v2.md` | Describe each flagged response in the discovery split, one call per response | 7,824 (7,420 answered, 404 refused); pilot 300 | 404 answered, 3 failed; plus 100 calibration | `PROMPT_TEXT`, `RESPONSE_TEXT` | `2876cb33a7624505` |
| `merge_group_v1.md` | Induce behaviours within one group of descriptions and assign every item | run 1: 116 (88 answered, 2 invalid, 26 refused); run 2: 116 (89, 2, 25) | run 1: 9; run 2: 8 | `ITEMS_JSONL` | `b79cff8d90d52988` |
| `merge_global_v1.md` | Merge one group's codebook into the running codebook | run 1: 101 (96 answered, 5 refused); run 2: 100 (96, 4) | 2 answered, 6 failed | `GROUP_ID`, `RUNNING_CODEBOOK_JSON`, `GROUP_CODEBOOK_JSON` | `c985f169cbe8240f` |
| `consolidate_v1.md` | Merge duplicates, drop rare behaviours, renumber F01… | run 1: 1 (refused); run 2: 1 (answered) | run 1: 1 (answered) | `RUNNING_CODEBOOK_JSON`, `POSSIBLE_DUPLICATES_JSON` | `f1810fe2ba73386d` |
| `label_v1.md` | Label one response with a codebook | 14,072, broken down below | 1,001 answered, 38 failed; plus 100 calibration | `FROZEN_CODEBOOK_JSON`, `PROMPT_TEXT`, `RESPONSE_TEXT` | `1c9b2e9ed76fc204` |
| `align_v1.md` | Align the run-1 and run-2 codebooks into shared concepts and parent categories (post hoc) | 1 (answered) | — | `RUN_A_JSON`, `RUN_B_JSON` | `3cd75dcb29403b4c` |

### `label_v1.md` calls by use

| Use | Codebook filled in | Claude calls | Sol fallback |
|---|---|---|---|
| Pass 1: all 9,838 responses flagged by judge pass 1 | frozen run-1 codebook | 9,838 (9,102 answered, 736 refused) | 725 answered |
| Repeat on the test split | frozen run-1 codebook | 978 (974, 4) | 4 |
| Dev split with the run-2 codebook (run comparison only) | run-2 consolidated codebook | 1,036 (917, 119) | 118 |
| GLM-5.3-Flash add-on: the 362 responses flagged by judge pass 1 or by the three-pass majority | frozen run-1 codebook | 362 (337, 25) | 25 |
| ML250: the 1,858 new translated-prompt responses flagged by the judge | frozen run-1 codebook | 1,858 (1,729, 129) | 129 |

**Outcome of pass 1.** It gives 9,827 labelled responses: 9,102 by Claude and
725 by Sol. Eleven stayed unlabelled.

**Calibration.** Sol also described 100 discovery responses and labelled 100
test responses that Claude had already done, to measure agreement between the
two annotators.

## Notes on individual prompts

- **`merge_group_v1.md`**
  - The text says "about 500 short descriptions", but both runs used groups of
    about 100. With groups of 500, every attempt was stopped by Anthropic's
    safety classifier.
  - The prompt was already frozen, so its wording was not changed.
  - Groups were stratified on system, condition, language and pressure class.
  - Run 1 used group seed 1 and run 2 used seed 2.
  - In each run, two answers failed validation twice. The pipeline code
    repaired them by a fixed rule, with no further model call:
    - duplicate behaviours and unknown ids were dropped;
    - behaviours with fewer than three member items were dropped;
    - items left without a behaviour went to `unassigned`.
- **`merge_global_v1.md`**
  - Groups were merged into a running codebook. Its saturation curve is the
    number of `new` decisions per group.
  - When Claude refused to combine one chain's behaviours into the shared
    codebook, those behaviours were appended unchanged with fresh ids. The
    consolidation step then reconciled them. No model call was made for this.
- **`consolidate_v1.md`**
  - Run 1's consolidation is the frozen 57-behaviour codebook.
  - Claude refused that call, so the frozen codebook was consolidated by GPT-5.6 Sol.
  - Run 2's consolidation (43 behaviours) was done by Claude.
- **`label_v1.md`**
  - [`inputs/label_codebook_57.json`](inputs/label_codebook_57.json) is the
    exact string that filled `{{FROZEN_CODEBOOK_JSON}}` in every call except
    the dev run-2 comparison.
  - It is the frozen codebook reduced to `behaviour_id`, `name`, `definition`,
    `include` and `exclude`, serialised with
    `json.dumps(..., ensure_ascii=False, indent=1)`.
  - It contains no closing wrapper tag, so it was substituted unchanged.
  - The full frozen codebook file has SHA-256
    `e7906c6ca591695038cac4e862ac68c66c05e86340b50475249657b4a92a67bf`.
- **`align_v1.md`**
  - One post-hoc call aligned the run-1 (57) and run-2 (43) codebooks from
    their definitions only, with no labels seen.
  - It returned 47 shared concepts and 11 parent categories (P01–P11): fabrication and unsupported claims, deceiving third parties, unsafe or uncritical compliance, manipulation and coercion, evaluation and integrity gaming, oversight and control evasion, privacy, surveillance and intrusion, identity and persona, harmful practical guidance, output-quality failures, and mitigating behaviours.
  - These were used to measure stability across the two runs.

**Item inputs**
- Describe and label calls received a response's `prompt_text` and
  `response_text` only.
- Merge calls received items as `{id, description, actions, request_handling}`,
  one JSON object per line, with opaque ids.

## SHA-256

```
2876cb33a76245058920e2fe845c29d27235c6f6e748d9ecee6339d6b2af1d61  describe_v2.md
b79cff8d90d5298883450cc94946933941670bf1697601c11ed41e2fa4c41d51  merge_group_v1.md
c985f169cbe8240f650b708c107d490802a8d24d08ef204a2b250fc8196ecf51  merge_global_v1.md
f1810fe2ba73386dc86feb96c224bd085cc7f712a2638a8cd1711c7e38660d89  consolidate_v1.md
1c9b2e9ed76fc2040be4b5cd187bbdbbe958e186c244f9bf596a97a5a1a401ec  label_v1.md
3cd75dcb29403b4ccdde73079ff75dfd94a646754fcafb6f1beb9cb449ea823d  align_v1.md
01536bb31c4bcdc2f100abfe47e36572f80671164c0b8bc88f662e933c55caa0  sol_fallback_preamble.txt
47a465b77dac2b595f5cb6e868ba6fbce4a1dccbf2d336ec748e294622142b44  inputs/label_codebook_57.json
```

Each prompt file is byte-identical to the file the run hashed before its first
call, and every logged call of its stage records the same hash.

## Not included

- **`describe_v1.md`.** It was used only in the three-item smoke test and the
  pilot on 300 dev responses. `describe_v2.md` replaced it before the run.
  `describe_v2.md` adds framing for the annotation task, a rule against
  repeating personal information, and a line marking the quoted record. The
  old file had SHA-256
  `9ae508c47d63397c29a3e3a139f959eb9a6da9da892b757bea31ec293a15134f`.
- **Abandoned and diagnostic merge calls.** These used `merge_group_v1.md` and
  are excluded from all outputs:
  - an abandoned first attempt with groups of 500 (6 calls, all stopped);
  - 5 probe calls on subgroups of 100 and 200.
- **The 18 parents and the eight groups (G1–G8).** The paper reports these, but
  they were not produced by the prompts in this folder.
