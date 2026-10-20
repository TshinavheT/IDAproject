// Builds PDF (and standalone HTML) versions of the two presentation decks.
// Each deck folder holds deck.json + slides/<id>.html in the slide format used by the online decks.
// Run from the project root:  node presentation/build_pdf.js   (needs Microsoft Edge)
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const PORT = 9334;

const DECKS = [
  { folder: "technical", out: "IDA117V_Technical_Presentation" },
  { folder: "story", out: "IDA117V_Project_Story_Presentation" },
];

// Images were uploaded to the online decks from these repository files.
const IMAGES = {
  "073a9a64513ef91592bd5c3da06a3de4": "reports/figures/app/app_profile_top.png",
  "08131562e572c5853baa3b1225343921": "reports/figures/app/app_profile_top.png",
  "0c8ededaa78dcee75a76930dfd5f3008": "reports/figures/app/app_dialog_recall.png",
  "c893a950d5b01d1825245580bd4e0179": "reports/figures/app/app_dialog_recall.png",
  "519dd64344f320e09b669f55874150bf": "reports/figures/app/app_explorer.png",
  "42823b287761adc4264b930a2b352465": "reports/figures/app/app_explorer.png",
  "ef54adb8ca341899ef1c314142f0f971": "reports/figures/app/app_overview_full.png",
  "2cae5b778fcd054e0a3f603acb2270fa": "reports/figures/q6_ablation.png",
  "093ee4409f789a578635b7019821c001": "reports/figures/q8_fairness.png",
  "f83f87dc29b660c4dad95b476d1d339e": "reports/figures/q4_model_comparison.png",
};

// Simple line icons standing in for the online decks' <x-icon> set.
const ICONS = {
  Warning: '<path d="M12 3 2 21h20L12 3z"/><path d="M12 10v5M12 18v.5"/>',
  Wrench: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z"/>',
  Home: '<path d="M3 11 12 3l9 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
  Clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/>',
  Lightbulb: '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0 0 12 3z"/>',
  Database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  Tool: '<path d="M3 21l8-8"/><path d="M13 3l8 8-4 4-8-8z"/>',
  Activity: '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
  Chart: '<path d="M5 20V11M11 20V5M17 20v-7M3 20h18"/>',
  Users: '<circle cx="9" cy="8" r="3.5"/><path d="M2 20c0-3.9 3.1-7 7-7s7 3.1 7 7"/><circle cx="17" cy="9" r="2.5"/><path d="M17 14c2.8 0 5 2.2 5 5"/>',
  Search: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-5-5"/>',
};

const CSS = `
@page { size: 1920px 1080px; margin: 0 }
* { margin: 0; box-sizing: border-box }
html, body { background: #777 }
section { width: 1920px; height: 1080px; position: relative; overflow: hidden; break-after: page }
section:last-of-type { break-after: auto }
aside { display: none }
h1 { font-size: 96px } h2 { font-size: 64px } h3 { font-size: 44px; font-weight: 600 } p { font-size: 32px; line-height: 1.4 }
ul, ol { padding-left: 1.2em }
table { border-collapse: collapse; width: 100% }
th, td { padding: 0.35em 0.6em; border-bottom: 1px solid rgba(0,0,0,0.12); vertical-align: top }
img { display: block }
svg { display: block; flex: none }
`;

function convertSlide(html, deckDir) {
  html = html.replace(/<aside>[\s\S]*?<\/aside>/g, "");
  html = html.replace(/src="\/_blob\/([0-9a-f]{32})"/g, (_, id) => {
    if (!IMAGES[id]) throw new Error(`No local file for image ${id}`);
    return `src="${path.relative(deckDir, path.join(ROOT, IMAGES[id])).split(path.sep).join("/")}"`;
  });
  html = html.replace(/<x-icon name="(\w+)" style="([^"]*)"><\/x-icon>/g, (_, name, style) => {
    if (!ICONS[name]) throw new Error(`No icon for ${name}`);
    return `<svg viewBox="0 0 24 24" style="${style}" fill="none" stroke="currentColor" stroke-width="2" ` +
      `stroke-linecap="round" stroke-linejoin="round" aria-label="${name}">${ICONS[name]}</svg>`;
  });
  html = html.replace(/<x-shape kind="arrow-right" style="([^"]*)"><\/x-shape>/g, (_, style) => {
    const fill = (style.match(/background:\s*([^;]+)/) || [, "#999"])[1].trim();
    const size = style.replace(/background:[^;]+;?/, "");
    return `<svg viewBox="0 0 100 50" preserveAspectRatio="none" style="${size}" aria-label="arrow">` +
      `<path d="M0 16h58V0l42 25-42 25V34H0z" fill="${fill}"/></svg>`;
  });
  if (/<x-/.test(html)) throw new Error("Unconverted custom element: " + html.match(/<x-[^>]*>/)[0]);
  return html;
}

function buildHtml(folder) {
  const deckDir = path.join(__dirname, folder);
  const deck = JSON.parse(fs.readFileSync(path.join(deckDir, "deck.json"), "utf8"));
  const fonts = Object.values(deck.faces).map((f) => `<link rel="stylesheet" href="${f.href}">`).join("\n");
  const slides = deck.order.map((id) => convertSlide(fs.readFileSync(path.join(deckDir, "slides", `${id}.html`), "utf8"), __dirname));
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>${deck.title}</title>\n${fonts}\n<style>${CSS}</style></head>` +
    `<body>\n${slides.join("\n")}\n</body></html>`;
  return { html, title: deck.title, count: slides.length };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function cdp(wsUrl) {
  const ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0;
  const pending = new Map();
  ws.onmessage = (m) => {
    const msg = JSON.parse(m.data);
    if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  };
  const send = (method, params = {}) => new Promise((res) => {
    const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params }));
  });
  return { send, close: () => ws.close() };
}

(async () => {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "edge-pdf-"));
  const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${profile}`, "--no-first-run", "--allow-file-access-from-files", "about:blank"], { stdio: "ignore" });
  try {
    let targets;
    for (let i = 0; i < 30 && !targets; i++) {
      try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); } catch { await sleep(500); }
    }
    const { send, close } = await cdp(targets.find((t) => t.type === "page").webSocketDebuggerUrl);
    await send("Page.enable");
    for (const deck of DECKS) {
      const { html, title, count } = buildHtml(deck.folder);
      const htmlPath = path.join(__dirname, `${deck.out}.html`);
      fs.writeFileSync(htmlPath, html);
      await send("Page.navigate", { url: "file:///" + htmlPath.split(path.sep).join("/") });
      for (let i = 0; i < 40; i++) {
        const r = await send("Runtime.evaluate", { awaitPromise: true, returnByValue: true, expression:
          "document.fonts.ready.then(() => document.readyState === 'complete' && [...document.images].every(i => i.complete && i.naturalWidth > 0))" });
        if (r.result && r.result.result && r.result.result.value) break;
        await sleep(500);
      }
      await sleep(800);
      const pdf = await send("Page.printToPDF", { printBackground: true, preferCSSPageSize: true,
        marginTop: 0, marginBottom: 0, marginLeft: 0, marginRight: 0 });
      if (!pdf.result) throw new Error(JSON.stringify(pdf.error));
      fs.writeFileSync(path.join(__dirname, `${deck.out}.pdf`), Buffer.from(pdf.result.data, "base64"));
      console.log(`${title}: ${count} slides -> presentation/${deck.out}.pdf`);
    }
    close();
  } finally {
    edge.kill();
  }
})().catch((e) => { console.error(e); process.exit(1); });
