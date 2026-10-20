// Builds the merged technical report (Questions 1-8, references, appendices) as an editable Word file.
// Cover details come from reports/report_config.json. Run from the project root:
//   node reports/build_full_report.js
// then make the PDF (updates the table of contents first):
//   powershell -File reports/export_report_pdf.ps1
const fs = require("fs");
const path = require("path");
const L = require("./full_report/lib");
const { Document, Packer, Paragraph, TextRun, AlignmentType, LevelFormat, Footer, PageNumber, TableOfContents, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, SectionType, PositionalTab, PositionalTabAlignment, PositionalTabRelativeTo,
  PositionalTabLeader } = L.docx;
const { FONT, BODY, SMALL, CONTENT_W, P, H1, runs } = L;

const ROOT = path.resolve(__dirname, "..");
const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, "report_config.json"), "utf8"));
const { references, appendices } = require("./full_report/appendix");
const q1q2 = require("./full_report/q1_q2");
const q3q5 = require("./full_report/q3_q5");
const q6q8 = require("./full_report/q6_q8");

const INK = "1F2A44", ACCENT = "C42D58";
const text = (t, o = {}) => new TextRun({ text: t, font: FONT, ...o });

// ------------------------------------------------------------------ cover
const grey = { style: BorderStyle.SINGLE, size: 4, color: "BFC6D4" };
const COLS = [6000, 3752];
const memberTable = new Table({
  width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: COLS,
  rows: [
    new TableRow({ tableHeader: true, children: ["Student name", "Student number"].map((h, i) => new TableCell({
      width: { size: COLS[i], type: WidthType.DXA }, shading: { fill: INK, type: ShadingType.CLEAR, color: "auto" },
      margins: { top: 70, bottom: 70, left: 100, right: 100 },
      borders: { top: grey, bottom: grey, left: grey, right: grey },
      children: [new Paragraph({ children: [text(h, { bold: true, color: "FFFFFF", size: 21 })] })] })) }),
    ...cfg.members.map((m) => new TableRow({ children: [m.name, m.studentNumber].map((v, i) => new TableCell({
      width: { size: COLS[i], type: WidthType.DXA }, margins: { top: 70, bottom: 70, left: 100, right: 100 },
      borders: { top: grey, bottom: grey, left: grey, right: grey },
      children: [new Paragraph({ children: [text(v, { size: 21 })] })] })) })),
  ],
});
const cover = [
  new Paragraph({ spacing: { before: 600, after: 120 }, children: [text("INTRODUCTION TO DATA SCIENCE  |  GROUP PROJECT", { bold: true, size: 22, color: ACCENT })] }),
  new Paragraph({ spacing: { after: 80 }, children: [text("Data Science for Better Service Delivery in South Africa", { size: 28, color: "555555" })] }),
  new Paragraph({ spacing: { before: 700, after: 160 }, children: [text("Predicting Municipal Audit Outcomes", { bold: true, size: 64, color: INK })] }),
  new Paragraph({ spacing: { after: 100 }, children: [text("Technical report: from a real public problem to a statistically validated machine-learning solution", { size: 28, color: "444444" })] }),
  new Paragraph({ spacing: { before: 500, after: 700 }, border: { left: { style: BorderStyle.SINGLE, size: 24, color: ACCENT, space: 12 } }, children: [
    text("Central challenge: how can responsible data science help a South African public-service stakeholder identify need, prioritise limited resources, or improve the reliability and reach of a service?", { italics: true, size: 22, color: "444444" })] }),
  memberTable,
  new Paragraph({ spacing: { before: 400, after: 60 }, children: [text(`Group: ${cfg.groupName}`, { size: 22, bold: true })] }),
  new Paragraph({ spacing: { after: 60 }, children: [text(`Lecturer: ${cfg.lecturer}`, { size: 22 })] }),
  new Paragraph({ spacing: { after: 60 }, children: [text(`Submission date: ${cfg.submissionDate}`, { size: 22 })] }),
  new Paragraph({ spacing: { before: 900 }, children: [text("IDA117V  ·  Technical report  ·  S2 2026", { size: 20, color: "777777" })] }),
];

// Contents page from the heading pages recorded by export_report_pdf.ps1 (a Word TOC field makes PDF export hang).
function contentsLines() {
  const file = path.join(__dirname, "report_headings.json");
  if (!fs.existsSync(file)) return [P("(Page numbers are added by reports/export_report_pdf.ps1.)")];
  let items = JSON.parse(fs.readFileSync(file, "utf8").replace(/^﻿/, ""));
  if (!Array.isArray(items)) items = [items];
  return items.map((h) => new Paragraph({
    spacing: { before: h.level === 1 ? 70 : 0, after: 10 },
    indent: { left: h.level === 1 ? 0 : 360 },
    children: [text(h.text, { size: h.level === 1 ? 20 : 18, bold: h.level === 1 }),
      new TextRun({ font: FONT, size: h.level === 1 ? 20 : 18, children: [new PositionalTab({ alignment: PositionalTabAlignment.RIGHT,
        relativeTo: PositionalTabRelativeTo.MARGIN, leader: PositionalTabLeader.DOT }), String(h.page)] })],
  }));
}

// ------------------------------------------------------------------ contents and declaration
const front = [
  new Paragraph({ pageBreakBefore: true, spacing: { after: 160 }, children: [text("Contents", { bold: true, size: 32, color: INK })] }),
  ...contentsLines(),
  new Paragraph({ spacing: { before: 360, after: 100 }, children: [text("Declaration and academic-integrity statement", { bold: true, size: 26, color: INK })] }),
  P("This report was prepared by the group named on the cover. Every dataset, library and external source is listed in the References. Questions 1 and 2 were written by team members; their text is reproduced here with minor corrections that bring it in line with the final results (listed in docs/report_merge_notes.md). The project contains no personal data, and no personal, confidential or access-controlled records were uploaded to public repositories or external tools."),
  P("**AI assistance.** AI tools (Claude, by Anthropic) were used to assist with research, coding and drafting. The team reviewed, ran and verified all code and results and takes responsibility for the content; individual contributions are set out in the signed contribution statement."),
];

// ------------------------------------------------------------------ assemble
const body = [
  ...q1q2(cfg), ...q3q5(), ...q6q8(cfg), ...references(),
];
const footer = (label) => new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
  text(`IDA117V Group Project · ${label} · page `, { size: 17, color: "777777" }),
  new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 17, color: "777777" })] })] });

const doc = new Document({
  creator: "IDA117V Group", title: "IDA117V Technical Report: Predicting Municipal Audit Outcomes",
  styles: {
    default: { document: { run: { font: FONT, size: BODY } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 29, bold: true, color: INK, font: FONT }, paragraph: { spacing: { before: 260, after: 110 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 23, bold: true, color: "3B6FEB", font: FONT }, paragraph: { spacing: { before: 170, after: 70 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 21, bold: true, color: INK, font: FONT }, paragraph: { spacing: { before: 120, after: 50 }, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 440, hanging: 220 } } } }] }] },
  sections: [
    { properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1077, right: 1077, bottom: 1077, left: 1077 } } },
      children: [...cover, ...front] },
    { properties: { type: SectionType.NEXT_PAGE, page: { size: { width: 11906, height: 16838 }, margin: { top: 1077, right: 1077, bottom: 1077, left: 1077 },
        pageNumbers: { start: 1 } } },
      footers: { default: footer("Technical report") }, children: body },
    { properties: { type: SectionType.NEXT_PAGE, page: { size: { width: 11906, height: 16838 }, margin: { top: 1077, right: 1077, bottom: 1077, left: 1077 } } },
      footers: { default: footer("Appendices") }, children: appendices() },
  ],
});

const out = process.env.OUT_DOCX || path.join(__dirname, "IDA117V_Technical_Report.docx");
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(out, buf); console.log("Wrote", out); });
