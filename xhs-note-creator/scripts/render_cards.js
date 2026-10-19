#!/usr/bin/env node
/** Render a local XHS draft into deterministic 1080x1440 PNG pages. */

const fs = require("node:fs");
const path = require("node:path");

const WIDTH = 1080;
const HEIGHT = 1440;
const LAYOUTS = {
  screenshots: { themes: ["light", "dark", "blur"], defaultTheme: "light" },
  code: { themes: ["sunset", "breeze", "mono"], defaultTheme: "sunset" },
  collection: { themes: ["paper"], defaultTheme: "paper" },
  text: { themes: ["paper", "ink"], defaultTheme: "paper" },
};
const IMAGE_TYPES = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif" };

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
  return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}

function inline(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

/** Split cards.md on `---` lines that are outside fenced code blocks. */
function splitSections(markdown) {
  const sections = [];
  let current = [];
  let fenced = false;
  for (const line of markdown.replace(/\r\n/g, "\n").split("\n")) {
    if (line.trim().startsWith("```")) fenced = !fenced;
    if (!fenced && /^---\s*$/.test(line)) {
      sections.push(current.join("\n"));
      current = [];
    } else {
      current.push(line);
    }
  }
  sections.push(current.join("\n"));
  return sections.map((section) => section.trim()).filter(Boolean);
}

/** Parse one page into structured blocks shared by every layout. */
function parseSection(text) {
  const page = { heading: "", subheading: "", images: [], code: [], blocks: [], meta: "", tags: [] };
  let paragraph = [];
  let list = null;
  let fence = null;
  const flushParagraph = () => {
    if (paragraph.length) page.blocks.push({ type: "p", text: paragraph.join("\n") });
    paragraph = [];
  };
  const flushList = () => {
    if (list) page.blocks.push(list);
    list = null;
  };

  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (fence) {
      if (trimmed.startsWith("```")) {
        page.code.push(fence);
        fence = null;
      } else {
        fence.lines.push(line);
      }
      continue;
    }
    if (trimmed.startsWith("```")) {
      flushParagraph();
      flushList();
      const [lang = "", ...title] = trimmed.slice(3).trim().split(/\s+/);
      fence = { lang, title: title.join(" "), lines: [] };
      continue;
    }
    const image = trimmed.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
    if (image) {
      flushParagraph();
      flushList();
      page.images.push({ alt: image[1], src: image[2] });
      continue;
    }
    if (!trimmed) {
      flushParagraph();
      flushList();
      continue;
    }
    if (/^meta:\s*/i.test(trimmed)) {
      page.meta = trimmed.replace(/^meta:\s*/i, "");
      continue;
    }
    if (/^tags:\s*/i.test(trimmed)) {
      page.tags = trimmed.replace(/^tags:\s*/i, "").split(/[,，]\s*/).filter(Boolean);
      continue;
    }
    if (trimmed.startsWith("# ") && !page.heading) {
      flushParagraph();
      flushList();
      page.heading = trimmed.slice(2);
      continue;
    }
    if (trimmed.startsWith("## ")) {
      flushParagraph();
      flushList();
      if (!page.subheading && !page.blocks.length) page.subheading = trimmed.slice(3);
      else page.blocks.push({ type: "h2", text: trimmed.slice(3) });
      continue;
    }
    if (trimmed.startsWith("> ")) {
      flushParagraph();
      flushList();
      page.blocks.push({ type: "quote", text: trimmed.slice(2) });
      continue;
    }
    const item = trimmed.match(/^(?:[-*]|\d+[.)])\s+(.*)$/);
    if (item) {
      flushParagraph();
      if (!list) list = { type: /^\d/.test(trimmed) ? "ol" : "ul", items: [] };
      list.items.push(item[1]);
      continue;
    }
    flushList();
    paragraph.push(trimmed);
  }
  if (fence) page.code.push(fence);
  flushParagraph();
  flushList();
  return page;
}

function blocksHtml(blocks) {
  return blocks
    .map((block) => {
      if (block.type === "p") return `<p>${block.text.split("\n").map(inline).join("<br>")}</p>`;
      if (block.type === "h2") return `<h2>${inline(block.text)}</h2>`;
      if (block.type === "quote") return `<blockquote>${inline(block.text)}</blockquote>`;
      const items = block.items.map((item) => {
        const row = item.match(/^(.*?)\s*(?:→|->)\s*(.*)$/);
        return row ? `<li class="row"><span>${inline(row[1])}</span><span>${inline(row[2])}</span></li>` : `<li>${inline(item)}</li>`;
      });
      return `<${block.type}>${items.join("")}</${block.type}>`;
    })
    .join("\n");
}

function imageDataUrl(draft, src) {
  const file = path.resolve(draft, src);
  const type = IMAGE_TYPES[path.extname(file).toLowerCase()];
  if (!type) usage(`unsupported image type for ${src}; use PNG, JPEG, WebP, or GIF`);
  if (!fs.existsSync(file)) usage(`image not found: ${src}`);
  return `data:${type};base64,${fs.readFileSync(file).toString("base64")}`;
}

/** Light shell-oriented highlighting: comments, strings, flags, and the command word. */
function highlightLine(line, lang) {
  const shell = ["", "sh", "bash", "zsh", "shell", "console"].includes(lang);
  const commentMatch = shell || ["py", "python", "rb", "yaml", "toml"].includes(lang) ? /(^|\s)(#.*)$/ : /(^|\s)(\/\/.*)$/;
  let code = line;
  let comment = "";
  const found = line.match(commentMatch);
  if (found && !/["'][^"']*$/.test(line.slice(0, found.index + found[1].length))) {
    code = line.slice(0, found.index + found[1].length);
    comment = found[2];
  }
  let html = "";
  const tokens = code.split(/("[^"]*"|'[^']*'|\s+)/).filter((token) => token !== "");
  let sawCommand = false;
  for (const token of tokens) {
    if (/^\s+$/.test(token)) html += token;
    else if (/^["']/.test(token)) html += `<span class="tok-str">${escapeHtml(token)}</span>`;
    else if (shell && /^--?[\w-]/.test(token)) html += `<span class="tok-flag">${escapeHtml(token)}</span>`;
    else if (shell && !sawCommand && !/^[$>]$/.test(token)) {
      html += `<span class="tok-cmd">${escapeHtml(token)}</span>`;
      sawCommand = true;
    } else html += escapeHtml(token);
    if (shell && /^(\||&&|;|\$\(|sudo)$/.test(token)) sawCommand = false;
  }
  if (comment) html += `<span class="tok-comment">${escapeHtml(comment)}</span>`;
  return html || " ";
}

function codeWindowHtml(block, fallbackTitle) {
  const lines = block.lines.map((line) => `<div class="line">${highlightLine(line, block.lang)}</div>`).join("");
  const title = block.title || fallbackTitle || block.lang || "";
  return `<div class="window"><div class="chrome"><i></i><i></i><i></i><span>${escapeHtml(title)}</span></div><pre class="code">${lines}</pre></div>`;
}

function coverText(manifest) {
  return `<header class="cover-text"><h1>${inline(manifest.title)}</h1>${manifest.subtitle ? `<p class="subtitle">${inline(manifest.subtitle)}</p>` : ""}</header>`;
}

const renderers = {
  screenshots: {
    cover(ctx) {
      const hero = ctx.manifest.cover_image || ctx.pages.find((page) => page.images.length)?.images[0]?.src;
      return `${coverText(ctx.manifest)}${hero ? `<div class="hero"><img src="${imageDataUrl(ctx.draft, hero)}"></div>` : ""}`;
    },
    page(ctx, page) {
      const image = page.images[0];
      if (!image) usage("screenshots layout: every page needs an image line like ![](source/shot.png)");
      const src = imageDataUrl(ctx.draft, image.src);
      const caption = page.blocks.filter((block) => block.type === "p").map((block) => inline(block.text)).join("<br>");
      return `${ctx.theme === "blur" ? `<div class="backdrop" style="background-image:url('${src}')"></div>` : ""}
        ${page.heading ? `<h2 class="shot-title">${inline(page.heading)}</h2>` : ""}
        <figure class="shot"><img src="${src}">${caption ? `<figcaption>${caption}</figcaption>` : ""}</figure>`;
    },
  },
  code: {
    cover(ctx) {
      const first = ctx.pages.find((page) => page.code.length);
      const preview = first ? codeWindowHtml({ ...first.code[0], lines: first.code[0].lines.slice(0, 7) }, first.heading) : "";
      return `${coverText(ctx.manifest)}<div class="preview">${preview}</div>`;
    },
    page(ctx, page) {
      if (!page.code.length) usage("code layout: every page needs a fenced code block");
      const windows = page.code.map((block) => codeWindowHtml(block, page.heading)).join("");
      return `<div class="stack fit">${windows}${page.blocks.length ? `<div class="note">${blocksHtml(page.blocks)}</div>` : ""}</div>`;
    },
  },
  collection: {
    cover(ctx) {
      const items = ctx.pages.filter((page) => page.images.length);
      const rows = items
        .map((page, i) => {
          return `<li><b>${String(i + 1).padStart(2, "0")}</b><strong>${inline(page.heading)}</strong><span>${inline(page.meta)}</span></li>`;
        })
        .join("");
      return `${ctx.manifest.kicker ? `<p class="kicker">${inline(ctx.manifest.kicker)}</p>` : ""}
        <h1>${inline(ctx.manifest.title)}</h1>${ctx.manifest.subtitle ? `<p class="subtitle">${inline(ctx.manifest.subtitle)}</p>` : ""}
        <ol class="toc">${rows}</ol>
        ${ctx.manifest.cover_note ? `<p class="cover-note">${inline(ctx.manifest.cover_note)}</p>` : ""}`;
    },
    page(ctx, page) {
      const items = ctx.pages.filter((p) => p.images.length);
      const head = `<div class="topline"><span>${inline(ctx.manifest.kicker || "")}</span>${page.meta ? `<b>${inline(page.meta)}</b>` : ""}</div>`;
      if (!page.images.length) {
        return `${head}<div class="summary fit"><h1>${inline(page.heading)}</h1>${page.subheading ? `<p class="lede">${inline(page.subheading)}</p>` : ""}${blocksHtml(page.blocks)}</div>`;
      }
      const position = items.indexOf(page);
      const tags = page.tags.map((tag) => `<span>${inline(tag)}</span>`).join("");
      return `${head}
        <div class="panel"><span class="item-no">${String(position + 1).padStart(2, "0")} / ${String(items.length).padStart(2, "0")}</span><img class="icon" src="${imageDataUrl(ctx.draft, page.images[0].src)}"></div>
        <div class="item-text fit"><h1 class="name">${inline(page.heading)}</h1>
        <div class="desc">${page.subheading ? `<p>${inline(page.subheading)}</p>` : ""}${blocksHtml(page.blocks)}</div>
        ${tags ? `<div class="tags">${tags}</div>` : ""}</div>`;
    },
  },
  text: {
    cover(ctx) {
      return coverText(ctx.manifest);
    },
    page(ctx, page) {
      const body = `${page.heading ? `<h1>${inline(page.heading)}</h1>` : ""}${page.subheading ? `<p class="lede">${inline(page.subheading)}</p>` : ""}${blocksHtml(page.blocks)}${page.code.map((block) => `<pre>${escapeHtml(block.lines.join("\n"))}</pre>`).join("")}`;
      return `<article class="fit">${body}</article>`;
    },
  },
};

function documentHtml(css, layout, theme, kind, body) {
  return `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body class="layout-${layout} theme-${theme} ${kind}"><main class="canvas">${body}</main></body></html>`;
}

/** Scale `.fit` content to the largest font size (up to data-max) that still fits the canvas. */
async function fitContent(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all([...document.images].map((img) => (img.complete ? null : new Promise((r) => { img.onload = img.onerror = r; }))));
    const canvas = document.querySelector(".canvas");
    const fit = document.querySelector(".fit");
    if (!fit) return;
    const limit = canvas.getBoundingClientRect().bottom - parseFloat(getComputedStyle(canvas).paddingBottom);
    const lines = [...fit.querySelectorAll(".line")];
    const wrapped = () => lines.filter((line) => line.getBoundingClientRect().height > parseFloat(getComputedStyle(line).lineHeight) * 1.5).length;
    const baseWrapped = wrapped();
    let scale = 1;
    // Enlarging must not wrap any extra code line; shrinking to fit is always allowed.
    const fits = () => canvas.scrollHeight <= canvas.clientHeight + 1 && fit.getBoundingClientRect().bottom <= limit + 1 && (scale <= 1 || wrapped() <= baseWrapped);
    const base = parseFloat(getComputedStyle(fit).fontSize);
    const max = parseFloat(getComputedStyle(fit).getPropertyValue("--fit-max")) || 1;
    let low = 0.55;
    let high = max;
    for (let i = 0; i < 12; i += 1) {
      const mid = (low + high) / 2;
      scale = mid;
      fit.style.fontSize = `${base * mid}px`;
      if (fits()) low = mid;
      else high = mid;
    }
    scale = low;
    fit.style.fontSize = `${base * low}px`;
  });
}

/** Tint collection icon panels with a pale version of the icon's average color. */
async function tintPanels(page) {
  await page.evaluate(() => {
    for (const img of document.querySelectorAll(".panel .icon")) {
      const c = document.createElement("canvas");
      c.width = c.height = 24;
      const g = c.getContext("2d");
      g.drawImage(img, 0, 0, 24, 24);
      const data = g.getImageData(0, 0, 24, 24).data;
      let r = 0, gr = 0, b = 0, n = 0;
      for (let i = 0; i < data.length; i += 4) {
        if (data[i + 3] < 128) continue;
        r += data[i]; gr += data[i + 1]; b += data[i + 2]; n += 1;
      }
      if (!n) continue;
      const mix = (v) => Math.round(v / n * 0.16 + 255 * 0.84);
      img.parentElement.style.background = `rgb(${mix(r)}, ${mix(gr)}, ${mix(b)})`;
    }
  });
}

async function main() {
  const draft = parseArgs(process.argv.slice(2));
  const manifestPath = path.join(draft, "manifest.json");
  const cardsPath = path.join(draft, "cards.md");
  if (!fs.existsSync(manifestPath) || !fs.existsSync(cardsPath)) usage("draft requires manifest.json and cards.md");
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const layout = manifest.layout || "text";
  if (!LAYOUTS[layout]) usage(`unknown layout "${layout}"; use ${Object.keys(LAYOUTS).join(", ")}`);
  const theme = LAYOUTS[layout].themes.includes(manifest.theme) ? manifest.theme : LAYOUTS[layout].defaultTheme;
  const withCover = manifest.cover !== false;
  const css = ["base.css", `${layout}.css`].map((name) => fs.readFileSync(path.resolve(__dirname, "../assets", name), "utf8")).join("\n");
  const pages = splitSections(fs.readFileSync(cardsPath, "utf8")).map(parseSection);
  if (!pages.length) usage("cards.md must contain at least one non-empty page");
  if (pages.length + (withCover ? 1 : 0) > 9) usage("cover plus pages cannot exceed 9 images");

  const output = path.join(draft, "output");
  fs.mkdirSync(output, { recursive: true });
  for (const name of fs.readdirSync(output)) {
    if (name === "cover.png" || /^card-\d{2}\.png$/.test(name)) fs.unlinkSync(path.join(output, name));
  }

  let chromium;
  try { ({ chromium } = require("playwright")); }
  catch { usage("Playwright is missing. Run npm install, then npx playwright install chromium."); }
  const browser = await chromium.launch({ headless: true });
  const browserPage = await browser.newPage({ viewport: { width: WIDTH, height: HEIGHT }, deviceScaleFactor: 1 });
  const ctx = { draft, manifest, pages, theme };
  const renderer = renderers[layout];
  const shots = [];
  const capture = async (kind, body, file) => {
    await browserPage.setContent(documentHtml(css, layout, theme, kind, body));
    await fitContent(browserPage);
    if (layout === "collection") await tintPanels(browserPage);
    await browserPage.screenshot({ path: path.join(output, file), type: "png" });
    shots.push(file);
  };

  if (withCover) await capture("is-cover", renderer.cover(ctx), "cover.png");
  for (const [index, page] of pages.entries()) {
    await capture("is-page", renderer.page(ctx, page, index), `card-${String(index + 1).padStart(2, "0")}.png`);
  }
  await browser.close();
  console.log(JSON.stringify({ draft, output, layout, theme, images: shots }, null, 2));
}

main().catch((error) => { console.error(error.stack || error.message); process.exit(1); });
