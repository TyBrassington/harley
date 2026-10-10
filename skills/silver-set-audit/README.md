# Silver-set audit skill

`audit-contrast-set` v0.10.1 is the Claude skill that audited the 1,601 sets
outside the gold set. The silver set contains 1,391 of them:

- 1,380 that the skill approved;
- 11 approved by people after the model refused to review them.

The reviewer was Claude Opus 5 at high effort. Each set got one decision,
`approve` or `deny`, with a short reason grounded in the prompt text. The
reviewer saw the five prompts, the language and the anchor role. It did not see
human decisions, behaviour labels or planner notes.

| Path | Contents |
|---|---|
| [`claude/audit-contrast-set/`](claude/audit-contrast-set/) | The skill: `SKILL.md` (procedure), `rubric_v6.md` (rubric, acceptance rules and verdict schema), `audit_set.py` (helper, standard library only) and its tests. |
| [`codex/audit-contrast-set/`](codex/audit-contrast-set/) | The same skill for Codex, byte-identical. |
| [`kit/`](kit/) | Batch audit and evaluation. `audit_eval.py` prepares prompt-only DEV and TEST batches, freezes predictions and scores agreement. `claude_audit_runner.py` runs the batches through the Claude CLI. See [`kit/README.md`](kit/README.md). |
| [`install.sh`](install.sh) | Copies the skill into `~/.claude/skills/` or `~/.codex/skills/`. |

Run the tests with `python -m pytest` from this folder. Only the `run` command
in `kit/audit_eval.py` calls a model.
