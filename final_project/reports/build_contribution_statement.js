// Builds reports/IDA117V_Contribution_Statement.docx (Q8.3): one page, signed by all members.
// Contributions are pre-filled only where the repository's commit history shows them; the team completes the rest.
// Run from the project root:  node reports/build_contribution_statement.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  AlignmentType, PageOrientation,
} = require("docx");

const FONT = "Calibri";
const border = { style: BorderStyle.SINGLE, size: 4, color: "8A93A6" };
const borders = { top: border, bottom: border, left: border, right: border };
const W = [2300, 1500, 2300, 5000, 2000, 1200]; // landscape A4 content width 14300 DXA

const cell = (text, w, header = false) => new TableCell({
  width: { size: w, type: WidthType.DXA }, borders,
  shading: header ? { fill: "2E3546", type: ShadingType.CLEAR, color: "auto" } : undefined,
  margins: { top: 50, bottom: 50, left: 80, right: 80 },
  children: String(text).split("\n").map((line) => new Paragraph({
    children: [new TextRun({ text: line, bold: header, color: header ? "FFFFFF" : "000000", size: 17, font: FONT })],
  })),
});

const members = [
  ["Thapelo ____________", "", "Data governance and preparation lead",
    "Data acquisition from the Municipal Money API and modelling dataset (src/build_modeling_dataset.py); Q2 data audit, " +
    "five EDA figures, time-based split and preprocessing pipeline (src/audit_q21_v2.py, visualize_q22_v2.py, split_q23_v2.py, " +
    "pipeline_q24.py). Commits: “Question 2 done”, “dataset”."],
  ["Pamela Khosa", "", "Modelling lead (first Question 3 run)",
    "First baseline and four-model notebook and Question 3 write-up (notebooks/archive). Commit: “Add files via upload”."],
  ["Tendani Tshinavhe", "", "Evaluation, deployment and reproducibility lead",
    "Q3 re-run on the time-based split (src/train_q3.py, neural.py, models.py); Q4 evaluation; Q5 optimisation and test; " +
    "Q6 ablations and McNemar's test; Q7 dashboard (app/) and 2025 forecast (src/forecast_next.py); Q8 fairness and " +
    "uncertainty analysis, reproducibility package (run_all.py, docs/) and report sections Q4–Q8."],
  ["", "", "", "Concept note, dataset card and feasibility check (Question 1): ______________________"],
  ["", "", "", ""],
  ["", "", "", ""],
];

const doc = new Document({
  creator: "IDA117V Group", title: "IDA117V Contribution Statement",
  styles: { default: { document: { run: { font: FONT, size: 20 } } } },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838, orientation: PageOrientation.LANDSCAPE },
      margin: { top: 900, right: 1000, bottom: 900, left: 1000 } } },
    children: [
      new Paragraph({ children: [new TextRun({ text: "IDA117V Group Project — Contribution Statement", bold: true, size: 30, color: "2E3546" })] }),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun({
        text: "Predicting Municipal Audit Outcomes · Group number: ______ · Lecturer: ____________________ · Submission date: ____________",
        size: 19, color: "444444" })] }),
      new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ size: 18, text:
        "Each member's role and specific outputs are listed below. Pre-filled entries come from the repository's commit history; " +
        "members must confirm or correct them before signing." })] }),
      new Table({
        width: { size: W.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: W,
        rows: [
          new TableRow({ tableHeader: true, children: ["Name", "Student number", "Role", "Specific outputs and evidence", "Signature", "Date"]
            .map((h, i) => cell(h, W[i], true)) }),
          ...members.map((m) => new TableRow({ height: { value: 640, rule: "atLeast" },
            children: [...m, "", ""].map((v, i) => cell(v, W[i])) })),
        ],
      }),
      new Paragraph({ spacing: { before: 200, after: 80 }, children: [new TextRun({ size: 18, text:
        "All members confirm that they understand and can defend the complete pipeline and user interface, that every dataset, " +
        "library and external source is referenced, and that the contributions above are accurate." })] }),
      new Paragraph({ children: [new TextRun({ size: 18, text:
        "AI assistance: an AI coding assistant (Claude, by Anthropic) was used to help write and debug code and draft parts of the " +
        "Question 4–8 text; commits made with its help are labelled in the repository. The team reviewed and verified all of it." })] }),
    ],
  }],
});

const out = path.resolve(__dirname, "IDA117V_Contribution_Statement.docx");
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(out, b); console.log("Wrote", out); });
