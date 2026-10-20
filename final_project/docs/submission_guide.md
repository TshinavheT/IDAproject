# Submission guide: how the pieces fit together and what to do before handing in

## 1. What goes to the lecturer (from the project template, section 4)

| Template item | Our file | Notes |
|---|---|---|
| Technical report (PDF, suggested 15–20 pages excluding cover, references, appendices) | `reports/IDA117V_Technical_Report.pdf` (editable: `.docx`) | Questions 1–8 in order, then references and appendices |
| Code (notebooks/scripts, README, requirements) | The GitHub repository (`final_project/` in `TshinavheT/IDAproject`) | `README.md`, `requirements.txt`, `run_all.py` reproduces everything |
| Deployed user interface (source, saved model, launch instructions, dependency file, stable link where available) | `app/`, `models/final_pipeline.joblib`, `app/requirements.txt` | Launch: `streamlit run app/app.py`. A hosted link is optional |
| Evidence bundle | `results/`, `reports/figures/`, `docs/experiment_log.md`, `docs/dataset_card.md`, `results/q6_paired_test_predictions.csv` | Already in the repository |
| Presentation (10–12 min plus questions, every member takes part) | `presentation/IDA117V_Technical_Presentation.pdf` (and the story deck) | Speaker notes in the online decks |
| Contribution statement (one page, signed by all members) | `reports/IDA117V_Contribution_Statement.docx` | Print, sign, scan |

Hosting is **not required**: Q7.4 accepts "a stable demonstration link **or** a locally reproducible launch command".

## 2. How everything links

```
              Municipal Money data (data/raw)
                          |
   python run_all.py  ->  results/  +  models/final_pipeline.joblib  +  reports/figures/
                          |                       |
          Technical report (numbers and         Dashboard (app/)  <- loads the saved model, shows the 2025 forecast
          figures come from results/)                |
                          \______________  ___________/
                                         \/
                       Slides: every claim in a slide is a number in the report;
                       the live demo shows the dashboard
```

| Slide (technical deck) | Report section | What to show |
|---|---|---|
| 2–3 Problem and task | Q1 | |
| 4 Data | Q1.3, Q2.1 | |
| 5 Split and the correction | Q2.3 | |
| 6–7 Models and what they learned | Q3, Q4.1 | |
| 8 Overfitting and tuning | Q4.4, Q5 | |
| 9 One-time test | Q5.3 | |
| 10 Ablation and McNemar | Q6 | |
| 11–12 Dashboard and live demo | Q7 | Dashboard (live) |
| 13–14 Fairness and recommendation | Q8.1 | |
| 15 Reproducibility and team | Q8.2–8.3 | `python run_all.py` |

The *story* deck (why we chose it, what it solves, how it works) is for a general audience; use it to introduce the
project to people who have not read the report, or as the first three slides of the talk.

## 3. Before you submit: in this order

1. **Teammates confirm the merge** (`docs/report_merge_notes.md`): Thapelo (Q2: the `prior_audit_outcome` decision) and Tran203 (Q1: one correction).
2. **Confirm lecturer approval** for the residual tabular neural network (the brief says "approved tabular neural network").
3. **Fill in the details**: `reports/report_config.json` (group number, lecturer, submission date, every member's name and student number), the slide placeholders, and the contribution statement.
4. **Optional: host the dashboard** (Streamlit Community Cloud, steps in the README) and put the link in `report_config.json` (`liveUrl`), the README and the slides.
5. **Rebuild the report**: `node reports/build_full_report.js`, then `powershell -File reports/export_report_pdf.ps1`.
6. **Final check from a clean copy**: clone the repository into an empty folder and run `python run_all.py`; open the dashboard.
7. **Hand in**: report PDF, repository link (or a zip), slides, signed contribution statement and the dashboard link if hosted.

## 4. Running the presentation (about 11 minutes)

| Minutes | Slides | Who |
|---|---|---|
| 0:00–1:30 | 1–3: problem, task, why | Project lead |
| 1:30–3:00 | 4–5: data and split | Data lead |
| 3:00–5:30 | 6–10: models, tuning, test, ablation, McNemar | Modelling and evaluation leads |
| 5:30–8:00 | 11–12: dashboard and **live demo** (about 2 minutes) | Deployment lead |
| 8:00–10:30 | 13–15: fairness, recommendation, reproducibility | Evaluation lead, then everyone |
| 10:30–end | Questions | Everyone: each member should be able to answer on any part |

Demo checklist: app running before you start; `app/samples/valid_cases.csv` and `invalid_case.csv` ready; slide 11 screenshots as a fallback.
