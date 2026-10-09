# Prompts

Each file is the exact text sent to the model in the runs that produced the
paper's results. Pilot, superseded and diagnostic prompts are left out; where a
newer version exists that was not used, the stage README says so. Each stage
README lists the model, its settings, the placeholders and the SHA-256 of every
file.

| Folder | Stage | Model | Paper |
|---|---|---|---|
| [`1_construction/`](1_construction/) | Building the contrast sets (pipeline v6) | Gemini 3.8 Flash, GPT-5.6 Sol | Building the benchmark |
| [`2_pressure_discovery/`](2_pressure_discovery/) | Discovering user pressures from the gold prompts | GPT-6 Astra | Discovering user pressures |
| [`3_misalignment_judge/`](3_misalignment_judge/) | Labelling each response | DeepSeek V4.1 Flash | Misalignment labels |
| [`4_behaviour_discovery/`](4_behaviour_discovery/) | Discovering behaviours in misaligned responses | Claude Opus 5.5 | Behaviour discovery |
| [`5_translation/`](5_translation/) | Translating gold sets for the language experiment | Gemini 3.8 Flash, Gemini 3.1 Pro | Translation experiment |

Placeholders appear as `{name}`, exactly as the code substituted them.
Pressure-discovery prompts have no placeholders; the JSON input follows the
`INPUT_JSON` line at the end of each file.
