import { saveAs } from "file-saver";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import { marked } from "marked";
import katex from "katex";
import "katex/dist/katex.min.css";
import type { GlobalNotes, SlideEnrichment, TopicNote } from "../types/slide";

function cleanLine(line: string) {
  // 去掉列表前缀、编号、分隔符“--”，避免误渲染粗体/列表
  return line
    .replace(/^\s*[-•]\s*/, "")
    .replace(/^\s*\d+[\.\)]\s*/, "")
    .replace(/^\s*--\s*/, "")
    .trim();
}

export function downloadMarkdown(topics: TopicNote[], globalNotes?: GlobalNotes | null) {
  const parts: string[] = [];
  // 目录
  if (topics.length) {
    parts.push("## 目录");
    topics
      .filter((t) => {
        const title = (t.title || "").toLowerCase();
        return (
          t.title &&
          !title.includes("目录") &&
          !title.includes("目录页") &&
          !title.includes("知识块") &&
          !title.includes("标题")
        );
      })
      .forEach((t) => {
        parts.push(`- ${t.title}`);
      });
    parts.push("");
  }
  parts.push("## 笔记内容");

  topics.forEach((topic, idx) => {
    parts.push(`## ${topic.title || "未命名"}`);
    if (topic.section) parts.push(`> 章节：${topic.section}`);
    parts.push("");
    parts.push("#### 内容");
    parts.push(cleanLine(topic.enrichment.summary));
    let inCode = false;
    const flushExpansion = (line: string) => {
      if (line.startsWith("```")) {
        parts.push(line);
        inCode = !inCode;
        return;
      }
      if (inCode) {
        parts.push(line);
      } else {
        const cleaned = cleanLine(line);
        if (cleaned) parts.push(cleaned);
      }
    };
    topic.enrichment.expansions.forEach(flushExpansion);
    parts.push("");
    if (topic.enrichment.search_snippets.length) {
      parts.push("### 检索片段");
      topic.enrichment.search_snippets.forEach((line) => {
        const cleaned = cleanLine(line);
        if (cleaned) parts.push(cleaned);
      });
      parts.push("");
    }
  });

  const md = parts.join("\n");
  const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
  saveAs(blob, "ppt-agent-notes.md");
}

export async function downloadPDF(topics: TopicNote[], globalNotes?: GlobalNotes | null) {
  marked.setOptions({ gfm: true, breaks: true });
  const normalizeMath = (md?: string | null) =>
    (md || "")
      .replace(/\\\(([\s\S]*?)\\\)/g, (_m, p1) => `$${p1}$`)
      .replace(/\\\[([\s\S]*?)\\\]/g, (_m, p1) => `$$\n${p1}\n$$`);
  const mdToHtml = (md?: string | null) => marked.parse(normalizeMath(md));
  const renderMathHtml = (html: string) =>
    html
      // 块级公式 $$...$$
      .replace(/\$\$([\s\S]+?)\$\$/g, (_m, expr) =>
        katex.renderToString(expr, { displayMode: true, throwOnError: false })
      )
      // 行内公式 $...$
      .replace(/\$([^\$\n]+?)\$/g, (_m, expr) =>
        katex.renderToString(expr, { displayMode: false, throwOnError: false })
      );
  const toHtmlWithMath = (md?: string | null) => renderMathHtml(mdToHtml(md));

  const container = document.createElement("div");
  container.style.padding = "20px";
  container.style.width = "800px";
  container.style.fontFamily = "'Microsoft YaHei', 'Noto Sans SC', sans-serif";
  container.style.background = "#fff";
  // 确保 KaTeX 样式可用于 html2canvas
  const katexLink = document.createElement("link");
  katexLink.rel = "stylesheet";
  katexLink.href = "https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/katex.min.css";
  document.head.appendChild(katexLink);

  const renderBlock = (html: string) => {
    const div = document.createElement("div");
    div.innerHTML = html;
    container.appendChild(div);
  };

  if (globalNotes) {
    renderBlock(`<h2>整体笔记</h2>${toHtmlWithMath(globalNotes.overview)}`);
    renderBlock(
      `<h3>知识点</h3><ul>${globalNotes.knowledge_points
        .map((k) => {
          const html = toHtmlWithMath(cleanLine(k));
          return `<li>${html.replace(/^<p>/, "").replace(/<\/p>$/, "")}</li>`;
        })
        .join("")}</ul>`
    );
    if (globalNotes.related_refs.length) {
      renderBlock(
        `<h3>关联/延伸</h3><ul>${globalNotes.related_refs
          .map((r) => {
            const html = toHtmlWithMath(cleanLine(r));
            return `<li>${html.replace(/^<p>/, "").replace(/<\/p>$/, "")}</li>`;
          })
          .join("")}</ul>`
      );
    }
  }

  topics.forEach((topic, idx) => {
    const combinedMd = ["#### 内容", topic.enrichment.summary || "", ...topic.enrichment.expansions]
      .filter(Boolean)
      .join("\n\n");
    const contentHtml = toHtmlWithMath(combinedMd);
    const searchHtml = topic.enrichment.search_snippets.length
      ? `<h4>检索片段</h4>${toHtmlWithMath(
          topic.enrichment.search_snippets.map((s) => `- ${s}`).join("\n")
        )}`
      : "";

    renderBlock(
      `<h2>知识块 ${idx + 1} - ${topic.title || "未命名"}</h2>` +
        (topic.section ? `<p><em>章节：${topic.section}</em></p>` : "") +
        contentHtml +
        searchHtml
    );
  });

  document.body.appendChild(container);
  const canvas = await html2canvas(container, { scale: 2 });
  const imgData = canvas.toDataURL("image/png");
  const pdf = new jsPDF("p", "pt", "a4");
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const imgWidth = pageWidth - 40;
  const imgHeight = (canvas.height * imgWidth) / canvas.width;
  let heightLeft = imgHeight;
  let position = 20;

  pdf.addImage(imgData, "PNG", 20, position, imgWidth, imgHeight);
  heightLeft -= pageHeight;
  while (heightLeft > -pageHeight) {
    position = heightLeft - imgHeight + 20;
    pdf.addPage();
    pdf.addImage(imgData, "PNG", 20, position, imgWidth, imgHeight);
    heightLeft -= pageHeight;
  }
  pdf.save("ppt-agent-notes.pdf");
  document.body.removeChild(container);
  // 清理临时样式
  document.head.removeChild(katexLink);
}
