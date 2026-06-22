#!/usr/bin/env node
/** Render a local XHS draft into deterministic 1080x1440 PNG cards. */

const fs = require("node:fs");
const path = require("node:path");

function usage(message) {
  if (message) console.error(`Error: ${message}`);
  console.error("Usage: node scripts/render_cards.js --draft drafts/<slug>");
  process.exit(1);
}

function parseArgs(argv) {
  if (argv.length !== 2 || argv[0] !== "--draft") usage();
  return path.resolve(argv[1]);
}

function escapeHtml(value) {
  return value.replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}

function inline(text) {
  return escapeHtml(text).replace(/`([^`]+)`/g, "<code>$1</code>");
}

function markdownToHtml(markdown) {
  const lines = markdown.replace(/\r\n/g, "\n").trim().split("\n");
  const parts = [];
  let list = false;
  let code = false;
  let codeLines = [];
  const closeList = () => { if (list) { parts.push("</ul>"); list = false; } };

  for (const line of lines) {
    if (line.trim().startsWith("```")) {
      closeList();
      if (code) { parts.push(`<pre>${escapeHtml(codeLines.join("\n"))}</pre>`); code = false; codeLines = []; }
      else code = true;
      continue;
    }
    if (code) { codeLines.push(line); continue; }
    if (!line.trim()) { closeList(); continue; }
    if (line.startsWith("# ")) { closeList(); parts.push(`<h1>${inline(line.slice(2))}</h1>`); continue; }
    if (line.startsWith("## ")) { closeList(); parts.push(`<h2>${inline(line.slice(3))}</h2>`); continue; }
    if (line.startsWith("> ")) { closeList(); parts.push(`<blockquote>${inline(line.slice(2))}</blockquote>`); continue; }
    if (/^[-*] /.test(line)) {
      if (!list) { parts.push("<ul>"); list = true; }
      parts.push(`<li>${inline(line.slice(2))}</li>`);
      continue;
    }
    closeList();
    parts.push(`<p>${inline(line)}</p>`);
  }
  if (code) parts.push(`<pre>${escapeHtml(codeLines.join("\n"))}</pre>`);
  closeList();
  return parts.join("\n");
}

function documentHtml(css, theme, body, footer, cover = false) {
  return `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body><main class="frame ${theme} ${cover ? "cover" : ""}"><section class="sheet">${body}</section><span class="footer">${escapeHtml(footer)}</span></main></body></html>`;
}

async function main() {
  const draft = parseArgs(process.argv.slice(2));
  const manifestPath = path.join(draft, "manifest.json");
  const cardsPath = path.join(draft, "cards.md");
  if (!fs.existsSync(manifestPath) || !fs.existsSync(cardsPath)) usage("draft requires manifest.json and cards.md");
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const theme = ["paper", "ink", "coral"].includes(manifest.theme) ? manifest.theme : "paper";
  const css = fs.readFileSync(path.resolve(__dirname, "../assets/card.css"), "utf8");
  const sections = fs.readFileSync(cardsPath, "utf8").split(/^---\s*$/m).map((part) => part.trim()).filter(Boolean);
  if (!sections.length) usage("cards.md must contain at least one non-empty card section");
  if (sections.length + 1 > 9) usage("cover plus body cards cannot exceed 9 images");

  const output = path.join(draft, "output");
  fs.mkdirSync(output, { recursive: true });
  for (const name of fs.readdirSync(output)) {
    if (name === "cover.png" || /^card-\d{2}\.png$/.test(name)) fs.unlinkSync(path.join(output, name));
  }

  let chromium;
  try { ({ chromium } = require("playwright")); }
  catch { usage("Playwright is missing. Run npm install, then npx playwright install chromium."); }
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1440 }, deviceScaleFactor: 1 });
  const cover = `<p class="eyebrow">XIAOHONGSHU NOTE</p><h1>${escapeHtml(manifest.title || "未命名笔记")}</h1><p class="subtitle">${escapeHtml(manifest.subtitle || "")}</p>`;
  await page.setContent(documentHtml(css, theme, cover, manifest.slug || "draft", true));
  await page.screenshot({ path: path.join(output, "cover.png"), type: "png" });
  for (const [index, section] of sections.entries()) {
    await page.setContent(documentHtml(css, theme, `<article class="card-content">${markdownToHtml(section)}</article>`, `${index + 1} / ${sections.length}`));
    await page.screenshot({ path: path.join(output, `card-${String(index + 1).padStart(2, "0")}.png`), type: "png" });
  }
  await browser.close();
  console.log(JSON.stringify({ draft, output, image_count: sections.length + 1 }, null, 2));
}

main().catch((error) => { console.error(error.stack || error.message); process.exit(1); });
