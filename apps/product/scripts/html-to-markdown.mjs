/**
 * Build-time HTML → Markdown conversion for the site's own rendered pages.
 *
 * The multi-page build emits regular, machine-generated HTML (scripts/shell.mjs,
 * scripts/render-city.mjs), so a focused tag-walking converter is enough: it
 * understands exactly the constructs those templates emit — headings, paragraphs,
 * lists (ul/ol), tables, definition lists, details/summary, blockquotes, inline
 * emphasis/code/links — strips decorative chrome (svg, canvas, buttons), decodes
 * entities, and collapses whitespace. Anything unrecognized unwraps to its text.
 */

const NAMED_ENTITIES = {
  amp: "&",
  lt: "<",
  gt: ">",
  quot: '"',
  apos: "'",
  nbsp: " ",
  ndash: "–",
  mdash: "—",
  lsquo: "‘",
  rsquo: "’",
  ldquo: "“",
  rdquo: "”",
  middot: "·",
  deg: "°",
  hellip: "…",
  times: "×",
  rarr: "→",
  larr: "←",
  sup2: "²",
};

function decodeEntities(text) {
  return text.replace(/&(#x?[0-9a-fA-F]+|[a-zA-Z]+);/g, (match, body) => {
    if (body.startsWith("#x") || body.startsWith("#X")) {
      const code = parseInt(body.slice(2), 16);
      return Number.isFinite(code) ? String.fromCodePoint(code) : match;
    }
    if (body.startsWith("#")) {
      const code = parseInt(body.slice(1), 10);
      return Number.isFinite(code) ? String.fromCodePoint(code) : match;
    }
    const named = NAMED_ENTITIES[body.toLowerCase()];
    return named ?? match;
  });
}

/** Strip tags/decode/collapse a fragment down to plain inline text. */
function plainText(fragment) {
  return decodeEntities(fragment.replace(/<[^>]+>/g, " "))
    .replace(/\s+/g, " ")
    .trim();
}

function attr(tag, name) {
  const match = tag.match(new RegExp(`${name}\\s*=\\s*("([^"]*)"|'([^']*)'|([^\\s>]+))`, "i"));
  return match ? (match[2] ?? match[3] ?? match[4] ?? "") : "";
}

function extractMain(html) {
  const match = html.match(/<main\s+id="content"[^>]*>([\s\S]*)<\/main>/i);
  if (!match) throw new Error('Rendered page is missing <main id="content">');
  return match[1];
}

/** Convert one flat <table>…</table> fragment into aligned pipe rows. */
function convertTable(fragment) {
  const rows = [];
  for (const rowMatch of fragment.matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/gi)) {
    const cells = [];
    let headerRow = false;
    for (const cellMatch of rowMatch[1].matchAll(/<(th|td)[^>]*>([\s\S]*?)<\/\1>/gi)) {
      if (cellMatch[1].toLowerCase() === "th") headerRow = true;
      cells.push(plainText(cellMatch[2]).replace(/\|/g, "\\|"));
    }
    if (cells.length) rows.push({ cells, headerRow });
  }
  if (!rows.length) return "";
  const width = Math.max(...rows.map((row) => row.cells.length));
  const pad = (cells) => [...cells, ...Array(width - cells.length).fill("")].join(" | ");
  const lines = [pad(rows[0].cells), Array(width).fill("---").join(" | ")];
  // Our tables always lead with a th header row; when one does not, the first
  // data row doubles as the visual header rather than being dropped.
  for (const row of rows[0].headerRow ? rows.slice(1) : rows) lines.push(pad(row.cells));
  return lines.join("\n");
}

/**
 * Convert a rendered page's <main> region to markdown body text. Callers
 * prepend the title/provenance front matter (see pageToMarkdown).
 */
export function htmlToMarkdown(html) {
  const main = html.match(/<main\s+id="content"[^>]*>([\s\S]*?)<\/main>/i);
  if (!main) throw new Error('Rendered page is missing <main id="content">');
  const source = main[1]
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<svg[\s\S]*?<\/svg>/gi, "")
    .replace(/<canvas[\s\S]*?<\/canvas>/gi, "");

  const out = [];
  let block = ""; // inline text accumulating for the current block
  let listStack = []; // { type: "ul" | "ol", index }
  let quoteDepth = 0;
  let skipUntil = -1; // index after a consumed region (e.g. </table>)
  const voided = new Set(); // interactive chrome whose inner text must not leak
  const linkHrefs = []; // per open <a>: href when a marker is pending, else null
  const SPACE_TAGS = new Set(["span", "small", "div", "section", "figure", "figcaption"]);
  const LINK_MARK = "\u0000"; // unambiguous pending-link sentinel

  /** Drop sentinels that plain-text extraction paths should never surface. */
  const cleanMarkers = (text) => text.split(LINK_MARK).join("");

  const flushBlock = () => {
    let text = block.replace(/\s+/g, " ").trim();
    block = "";
    if (text) out.push(`${"> ".repeat(quoteDepth)}${text}`);
  };

  const openList = (type) => {
    flushBlock();
    listStack.push({ type, index: 0 });
  };
  const closeList = () => {
    flushBlock();
    listStack.pop();
  };

  const marker = () => {
    const top = listStack[listStack.length - 1];
    if (!top) return null;
    top.index += 1;
    return `${top.type === "ol" ? `${top.index}.` : "-"} `;
  };

  const emitHeading = (level) => {
    const heading = cleanMarkers(plainText(block))
      .replace(/[`*]/g, "")
      .replace(/\s+/g, " ")
      .trim();
    block = "";
    if (heading) out.push(`${"#".repeat(level)} ${heading}`);
  };

  const tagPattern = /<\/?\s*([a-zA-Z0-9-]+)([^>]*)>|([^<]+)/g;

  let position = 0;
  while (position < source.length) {
    if (position < skipUntil) {
      // Jump past a region consumed by a structural handler.
      tagPattern.lastIndex = skipUntil;
      position = skipUntil;
      continue;
    }
    const match = tagPattern.exec(source);
    if (!match) break;
    position = tagPattern.lastIndex;

    if (match[3] !== undefined) {
      block += decodeEntities(match[3]).replace(/\s+/g, " ");
      continue;
    }

    const [, rawName, rawAttrs] = match;
    const tag = rawName.toLowerCase();
    const isClose = match[0][1] === "/";
    if (isClose && voided.has(tag)) {
      voided.delete(tag);
      continue;
    }

    switch (tag) {
      case "h1":
      case "h2":
      case "h3":
      case "h4":
      case "h5": {
        const level = Number(tag[1]);
        if (!isClose) {
          flushBlock();
          block = "";
        } else {
          emitHeading(level);
        }
        break;
      }
      case "p":
      case "section":
      case "div":
      case "figure":
      case "figcaption":
        if (isClose) flushBlock();
        break;
      case "br":
        block += "\n";
        break;
      case "hr":
        flushBlock();
        out.push("---");
        break;
      case "ul":
      case "ol":
        if (isClose) closeList();
        else openList(tag);
        break;
      case "li":
        if (!isClose) {
          flushBlock();
          block = marker() ?? "";
        } else {
          flushBlock();
        }
        break;
      case "blockquote":
        if (!isClose) {
          flushBlock();
          quoteDepth += 1;
        } else {
          flushBlock();
          quoteDepth = Math.max(0, quoteDepth - 1);
        }
        break;
      case "summary":
        if (!isClose) {
          flushBlock();
          block = "";
        } else {
          const label = cleanMarkers(plainText(block));
          block = "";
          if (label) out.push(`**${label}**`);
        }
        break;
      case "dt":
        if (!isClose) {
          flushBlock();
          block = "";
        } else {
          const term = cleanMarkers(plainText(block));
          block = "";
          if (term) out.push(`**${term}**`);
        }
        break;
      case "dd":
        if (!isClose) {
          flushBlock();
          block = "";
        } else {
          flushBlock();
        }
        break;
      case "a": {
        if (!isClose) {
          const href = attr(rawAttrs, "href");
          const marked = Boolean(href) && !href.startsWith("#") && !voided.size;
          linkHrefs.push(marked ? href : null);
          if (marked) block += LINK_MARK;
        } else {
          const href = linkHrefs.pop();
          const openIndex = href ? block.lastIndexOf(LINK_MARK) : -1;
          if (openIndex === -1) break;
          const label = cleanMarkers(plainText(block.slice(openIndex + 1)));
          const before = block.slice(0, openIndex);
          block =
            label && !href.startsWith("#")
              ? `${before}[${label}](${href})`
              : before;
        }
        break;
      }
      case "strong":
      case "b":
        block += "**";
        break;
      case "em":
      case "i":
        block += "*";
        break;
      case "code":
        block += "`";
        break;
      case "table": {
        flushBlock();
        const endTag = "</table>";
        const end = source.toLowerCase().indexOf(endTag, position);
        if (end === -1) break;
        const converted = convertTable(source.slice(position - match[0].length, end));
        if (converted) out.push(converted);
        skipUntil = end + endTag.length;
        break;
      }
      case "button":
      case "select":
      case "option":
      case "datalist":
        if (!isClose && !match[0].endsWith("/>")) voided.add(tag);
        break;
      default:
        // Unwrapped containers need word boundaries where the template had none.
        if (SPACE_TAGS.has(tag)) block += " ";
        break;
    }
  }
  flushBlock();

  return out
    .join("\n")
    .replace(/\u0000/g, "")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

/** Render one built page as its full markdown twin. */
export function pageToMarkdown(html, { origin, path }) {
  const title = plainText(html.match(/<title>([\s\S]*?)<\/title>/i)?.[1] ?? "Urban Signal");
  const description = plainText(html.match(/name="description"\s+content="([^"]*)"/i)?.[1] ?? "");
  const canonical = `${origin}${path}`;
  const body = htmlToMarkdown(html);
  const lines = [`# ${title}`, ""];
  if (description) lines.push(description, "");
  lines.push(
    `> Markdown rendering of [${canonical}](${canonical}); the HTML page is canonical.`,
    "> Machine-readable facts: `/facts.json` · Full agent context: `/llms-full.txt` · API catalog: `/.well-known/api-catalog`",
    "",
    body,
    ""
  );
  return lines.join("\n");
}
