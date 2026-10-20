// Shared helpers and data loaders for the full technical report (see build_full_report.js).
const fs = require("fs");
const path = require("path");
const docx = require("docx");
const {
  Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType, AlignmentType,
  ImageRun, BorderStyle, VerticalAlign,
} = docx;

const ROOT = path.resolve(__dirname, "..", "..");
const FONT = "Calibri";
const BODY = 20;      // 10 pt
const SMALL = 17;     // 8.5 pt
const CONTENT_W = 9752; // A4 minus 2 x 1077 DXA margins

const readJson = (f) => JSON.parse(fs.readFileSync(path.join(ROOT, "results", f), "utf8"));

function parseCsv(text) {
  const rows = [];
  let row = [], cell = "", quoted = false;
  text = text.trim();
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (ch === '"') quoted = false;
      else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(cell); rows.push(row); row = []; cell = "";
    } else cell += ch;
  }
  row.push(cell); rows.push(row);
  const [head, ...body] = rows;
  return body.map((r) => Object.fromEntries(r.map((v, i) => [head[i], v === "" || isNaN(+v) ? v : +v])));
}
const readCsv = (f) => parseCsv(fs.readFileSync(path.join(ROOT, "results", f), "utf8"));

const f3 = (x) => Number(x).toFixed(3);
const pct = (x, d = 1) => (Number(x) * 100).toFixed(d) + "%";
const sgn = (x) => (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(3);

// **bold** and _italic_; underscores inside identifiers (e.g. not_at_risk, audit_q21_v2.py) are left alone.
const ITALIC = /^_[^_\n]+_$/;
const runs = (text, extra = {}) => String(text).split(/(\*\*[^*]+\*\*|(?<![\w/.])_[^_\n]+?_(?![\w]))/).filter(Boolean).map((s) =>
  s.startsWith("**") ? new TextRun({ text: s.slice(2, -2), bold: true, ...extra })
    : ITALIC.test(s) ? new TextRun({ text: s.slice(1, -1), italics: true, ...extra })
      : new TextRun({ text: s, ...extra }));

const P = (text, opts = {}) => new Paragraph({ children: runs(text), spacing: { after: 90, line: 252 }, ...opts });
const H1 = (text, opts = {}) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)], keepNext: true, ...opts });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)], keepNext: true });
const H3 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(text)], keepNext: true });
const B = (text) => new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: runs(text), spacing: { after: 50, line: 252 } });
const caption = (text) => new Paragraph({
  children: [new TextRun({ text, italics: true, size: SMALL, color: "555555" })],
  alignment: AlignmentType.CENTER, spacing: { before: 40, after: 150 },
});

const border = { style: BorderStyle.SINGLE, size: 4, color: "BFC6D4" };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

// widths: DXA per column (should sum to CONTENT_W). size: font size in half-points.
function table(headers, rows, widths, { bold = [], size = SMALL, align = [] } = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (text, w, header, boldRow, i) => new TableCell({
    width: { size: w, type: WidthType.DXA }, borders,
    shading: header ? { fill: "2E3546", type: ShadingType.CLEAR, color: "auto" }
      : boldRow ? { fill: "E8F1FD", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 35, bottom: 35, left: 70, right: 70 },
    verticalAlign: VerticalAlign.TOP,
    children: String(text).split("\n").map((line) => new Paragraph({
      alignment: align[i] === "right" ? AlignmentType.RIGHT : AlignmentType.LEFT,
      children: header || boldRow
        ? [new TextRun({ text: line, bold: true, color: header ? "FFFFFF" : "000000", size })]
        : runs(line, { size }),
    })),
  });
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, cantSplit: true, children: headers.map((h, i) => cell(h, widths[i], true, false, i)) }),
      ...rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((v, i) => cell(v, widths[i], false, bold.includes(ri), i)) })),
    ],
  });
}

function imageInfo(file) {
  const buf = fs.readFileSync(file);
  if (buf[0] === 0x89) return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20), type: "png", buf };
  let i = 2;
  while (i < buf.length) {
    const marker = buf[i + 1], len = buf.readUInt16BE(i + 2);
    if (marker >= 0xc0 && marker <= 0xc3) return { h: buf.readUInt16BE(i + 5), w: buf.readUInt16BE(i + 7), type: "jpg", buf };
    i += 2 + len;
  }
  throw new Error("Unknown image: " + file);
}
function imageRun(rel, width) {
  const img = imageInfo(path.join(ROOT, rel));
  return new ImageRun({
    type: img.type, data: img.buf,
    transformation: { width, height: Math.round(width * img.h / img.w) },
    altText: { title: path.basename(rel), description: path.basename(rel), name: path.basename(rel) },
  });
}
// Image on its own, centred, with a caption underneath.
function figure(rel, text, width = 560) {
  return [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60 }, keepNext: true, children: [imageRun(rel, width)] }), caption(text)];
}
// Image on the left, explanatory paragraphs on the right (used where a figure needs its interpretation beside it).
function sideFigure(rel, capText, paragraphs, imgWidth = 340, imgCol = 4000) {
  const textCol = CONTENT_W - imgCol;
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: [imgCol, textCol],
    rows: [new TableRow({ cantSplit: true, children: [
      new TableCell({ width: { size: imgCol, type: WidthType.DXA }, borders: noBorders, margins: { top: 40, bottom: 40, left: 0, right: 100 },
        children: [new Paragraph({ children: [imageRun(rel, imgWidth)] }),
          new Paragraph({ spacing: { before: 30 }, children: [new TextRun({ text: capText, italics: true, size: SMALL, color: "555555" })] })] }),
      new TableCell({ width: { size: textCol, type: WidthType.DXA }, borders: noBorders, margins: { top: 40, bottom: 40, left: 100, right: 0 },
        children: paragraphs.map((t) => new Paragraph({ children: runs(t, { size: 19 }), spacing: { after: 70, line: 245 } })) }),
    ] })],
  });
}
// Two images side by side, each with its own caption.
function twoFigures(a, b, width = 300) {
  const half = CONTENT_W / 2;
  const cell = ({ rel, text }) => new TableCell({
    width: { size: half, type: WidthType.DXA }, borders: noBorders, margins: { top: 40, bottom: 40, left: 40, right: 40 },
    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [imageRun(rel, width)] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 30 }, children: [new TextRun({ text, italics: true, size: SMALL, color: "555555" })] })],
  });
  return new Table({ width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: [half, half],
    rows: [new TableRow({ cantSplit: true, children: [cell(a), cell(b)] })] });
}
const spacer = (after = 60) => new Paragraph({ spacing: { after }, children: [] });

module.exports = {
  docx, ROOT, FONT, BODY, SMALL, CONTENT_W, readJson, readCsv, parseCsv, f3, pct, sgn, runs,
  P, H1, H2, H3, B, caption, table, figure, sideFigure, twoFigures, imageRun, spacer, noBorders,
};
