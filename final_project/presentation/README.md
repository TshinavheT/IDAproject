# Presentations

| File | Deck | Use it for |
|---|---|---|
| [IDA117V_Project_Story_Presentation.pdf](IDA117V_Project_Story_Presentation.pdf) | **Seeing municipal audit failure coming** (12 slides) | Why we chose the project, what problems it solves and how it works — for any audience |
| [IDA117V_Technical_Presentation.pdf](IDA117V_Technical_Presentation.pdf) | **Predicting municipal audit outcomes** (15 slides) | The marked 10–12 minute defence: data, split, models, evaluation, McNemar, dashboard demo, fairness, recommendation |

Speaker notes are in the online decks (open from the owner's Share menu; they can also be downloaded as PowerPoint):
- Story deck: https://claude.ai/artifact/7B8NK1fUX4rx18jdGMhC2K
- Technical deck: https://claude.ai/artifact/Kp9praEutWvN9bFA9tCMPU

The slide sources are in `story/` and `technical/` (`deck.json` + one HTML file per slide, notes in each slide's `<aside>`).
To rebuild the PDFs and standalone HTML versions after editing a slide (needs Microsoft Edge):

```bash
node presentation/build_pdf.js
```

Presenters are named on each slide footer and in the speaker notes, following the agreed roles in the contribution statement.
