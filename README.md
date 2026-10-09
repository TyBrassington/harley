# HARLEY

Materials for HARLEY, a benchmark of 1,591 contrast sets anchored in real user
turns from WildChat, LMSYS-Chat-1M and ShareGPT, in 16 languages. Each set keeps
a request fixed and varies either its circumstances or its wording, so that a
change in model behaviour can be traced to the pressure that differs between
prompts. A 200-set core was verified by people; the other 1,391 sets were
audited by a model.

| Folder | Contents |
|---|---|
| [`prompts/`](prompts/) | Every model prompt used to build and analyse the benchmark, copied verbatim from the runs behind the paper, with the inputs that fill their placeholders. |
| [`skills/`](skills/) | The Claude skill used to audit the silver sets. |

## Paper

Anonymous for review.
