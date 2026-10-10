# Translation prompt

[`translation.txt`](translation.txt) (originally `translation_v1.txt`; SHA-256 first 16: `d54b998d80d01690`)
translated the gold sets for the language experiment. It runs once per set and
target language. All five prompts of a set are translated together, directly
from the source language into the target language.

## Models and settings

- Models: `gemini-3.8-flash` and `gemini-3.1-pro-preview`, both given the same
  prompt.
- Vertex AI batch, temperature 0.1, top-p 0.8, thinking level high.
- Each model produced its own translation of every set. The paper uses the
  translations of the model that scored better.

## Placeholders

| Placeholder | What fills it |
|---|---|
| `{source_language}`, `{target_language}` | Language names. |
| `{five_prompts}` | The set's five prompts. |
| `{variant_definition}` | Definitions of the five conditions. To be added. |
| `{manner_equivalence_source}`, `{manner_equivalence_target}` | Per-language guidance on style, politeness and careless writing. To be added. |
