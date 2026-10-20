// Captures dashboard screenshots for the report with headless Microsoft Edge (DevTools protocol).
// Start the app first (streamlit run app/app.py), then from the project root:
//   node reports/capture_app_screenshots.js
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const BASE = "http://localhost:8501";
const OUT = path.resolve(__dirname, "figures", "app");
const PORT = 9333;
const WIDTH = 1400;

const SCROLL = (y) => `[document.querySelector('[data-testid="stMain"]'), document.querySelector('[data-testid="stAppViewContainer"]'), document.scrollingElement].forEach(e => e && (e.scrollTop = ${y}))`;

// name, url path, height of the capture, optional action before the capture: a JS string, or a list of steps
// ({js}, {text} typed into the focused element, {key} Enter/Tab, {wait} ms)
const SHOTS = [
  ["app_overview_full", "/", 2080],
  ["app_dialog_recall", "/", 900,
    `[...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'Details ›' &&
       b.closest('[data-testid="stVerticalBlock"]').innerText.includes('Recall')).click()`],
  ["app_dialog_flagged", "/", 900,
    `[...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'See list ›').click()`],
  ["app_explorer", "/explore", 1650],
  ["app_profile_top", "/municipality?code=GT421", 1150],
  ["app_profile_trends", "/municipality?code=GT421", 1150, `[document.querySelector('[data-testid="stMain"]'), document.querySelector('[data-testid="stAppViewContainer"]'), document.scrollingElement].forEach(e => e && (e.scrollTop = 1060))`],
  // Risk check: choose Emfuleni in the selectbox and capture the prediction result
  ["app_risk_check_result", "/risk-check", 1150, [
    { click: 'input[aria-label="Municipality"]' }, { wait: 800 },
    { text: "Emfuleni" }, { wait: 1500 }, { key: "Enter" }, { wait: 6000 },
    { js: SCROLL(760) }, { wait: 1500 }]],
  // Risk check: invalid manual entry (total expenditure = 0) and the error message
  ["app_invalid_input", "/risk-check", 720, [
    { click: '[data-testid="stTab"][id$="-tab-1"]' }, { wait: 2000 },
    { click: 'input[aria-label="Total expenditure (R million)"]' },
    { js: `document.querySelector('input[aria-label="Total expenditure (R million)"]').select()` },
    { text: "0" }, { key: "Tab" }, { wait: 800 },
    { click: '[data-testid="stBaseButton-secondaryFormSubmit"]' },
    { wait: 4000 }]],
];

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

async function waitRendered(send) {
  // Ready when Streamlit is idle, nothing is a loading placeholder, every chart and table has drawn,
  // and the page has stayed the same for two checks in a row.
  let last = null;
  for (let i = 0; i < 90; i++) {
    const r = await send("Runtime.evaluate", { returnByValue: true, expression: `(() => {
      const app = document.querySelector('[data-testid="stMain"]');
      if (!app || document.querySelector('[data-testid="stStatusWidget"]')) return null;
      if (document.querySelectorAll('[data-testid="stSkeleton"], .stSkeleton').length) return null;
      const vis = (e) => e.offsetParent !== null; const plotEls = [...document.querySelectorAll('.js-plotly-plot')].filter(vis); const plots = plotEls.length;
      const drawn = plotEls.filter((e) => e.querySelector('.main-svg')).length;
      const tableEls = [...document.querySelectorAll('[data-testid="stDataFrame"]')].filter(vis); const tables = tableEls.length;
      const tablesDrawn = tableEls.filter((e) => e.querySelector('canvas')).length;
      if (drawn < plots || tablesDrawn < tables) return null;
      return app.innerText.length + ':' + plots + ':' + tables + ':' + app.scrollHeight;
    })()` });
    const sig = r.result && r.result.result && r.result.result.value;
    if (sig && sig === last) return;
    last = sig;
    await sleep(1000);
  }
  throw new Error("page did not finish rendering");
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "edge-shots-"));
  const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", "--hide-scrollbars", `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${profile}`, "--no-first-run", "about:blank"], { stdio: "ignore" });
  try {
    let targets;
    for (let i = 0; i < 30; i++) {
      try { targets = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); break; } catch { await sleep(500); }
    }
    const page = targets.find((t) => t.type === "page");
    const { send, close } = await cdp(page.webSocketDebuggerUrl);
    await send("Page.enable");
    await send("Runtime.enable");
    const only = process.argv.slice(2);
    for (const [name, url, height, action] of SHOTS.filter(([n]) => !only.length || only.includes(n))) {
      await send("Emulation.setDeviceMetricsOverride", { width: WIDTH, height, deviceScaleFactor: 1.5, mobile: false });
      await send("Page.navigate", { url: BASE + url });
      await sleep(2500);
      await waitRendered(send);
      await sleep(1500);
      if (action) {
        const KEYS = { Enter: 13, Tab: 9 };
        for (const step of Array.isArray(action) ? action : [{ js: action }]) {
          if (step.js) await send("Runtime.evaluate", { expression: step.js });
          if (step.click) {  // a real mouse click at the centre of the first matching element
            let xy = null;
            for (let i = 0; i < 40 && !xy; i++) {  // wait up to 20 s for the element to appear
              const r = await send("Runtime.evaluate", { returnByValue: true, expression:
                `(() => { const e = document.querySelector(${JSON.stringify(step.click)}); if (!e) return null; const b = e.getBoundingClientRect(); return [b.x + b.width / 2, b.y + b.height / 2]; })()` });
              xy = r.result && r.result.result && r.result.result.value;
              if (!xy) await sleep(500);
            }
            if (!xy) throw new Error("element not found: " + step.click);
            const [x, y] = xy;
            for (const type of ["mousePressed", "mouseReleased"]) await send("Input.dispatchMouseEvent", { type, x, y, button: "left", clickCount: 1 });
          }
          if (step.text) await send("Input.insertText", { text: step.text });
          if (step.key) for (const type of ["keyDown", "keyUp"]) await send("Input.dispatchKeyEvent",
            { type, key: step.key, code: step.key, windowsVirtualKeyCode: KEYS[step.key], nativeVirtualKeyCode: KEYS[step.key] });
          await sleep(step.wait || 300);
        }
        await sleep(2000);
        await waitRendered(send);
        await sleep(2500);
      }
      const shot = await send("Page.captureScreenshot", { format: "png" });
      // A blank page compresses to a tiny PNG; refuse to save it (happens if the app is not responding).
      if (shot.result.data.length < 40000) throw new Error(`${name}: screenshot looks blank (${shot.result.data.length} bytes); is the app running and responsive?`);
      fs.writeFileSync(path.join(OUT, `${name}.png`), Buffer.from(shot.result.data, "base64"));
      console.log("saved", name);
    }
    close();
  } finally {
    edge.kill();
  }
})().catch((e) => { console.error(e); process.exit(1); });
