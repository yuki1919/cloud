import { useState, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import type { SlideEnrichment } from "../types/slide";

type Props = {
  slide: SlideEnrichment;
};

// 规范公式分隔符：\(...\) -> $...$，\[...\] -> $$...$$
const normalizeMath = (md: string) =>
  md
    .replace(/\\\(([^)]*)\\\)/g, (_m, p1) => `$${p1}$`)
    .replace(/\\\[([\s\S]*?)\\\]/g, (_m, p1) => `$$\n${p1}\n$$`)
    .replace(/\n\$\s*\n([\s\S]*?)\n\$\s*\n/g, (_m, p1) => `\n$$\n${p1}\n$$\n`);

export function SlideCard({ slide }: Props) {
  const [open, setOpen] = useState(false);
  const contentMd = useMemo(() => {
    const pieces = [slide.enrichment.summary, ...slide.enrichment.expansions].filter(Boolean);
    return normalizeMath(pieces.join("\n\n"));
  }, [slide.enrichment.summary, slide.enrichment.expansions]);
  return (
    <div className="card">
      <div className="card-header" onClick={() => setOpen((v) => !v)}>
        <div>
          <div className="eyebrow">第 {slide.slide_number} 页</div>
          <h3>{slide.title || "未命名"}</h3>
          {slide.section && <div className="muted">章节：{slide.section}</div>}
        </div>
        <button className="ghost">{open ? "收起" : "展开"}</button>
      </div>
      {open && (
        <div className="card-body">
          <section>
            <h4>内容</h4>
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex]}>
              {contentMd || "（空）"}
            </ReactMarkdown>
          </section>
          {slide.enrichment.search_snippets.length > 0 && (
            <section>
              <h4>检索片段</h4>
              <ul className="muted">
                {slide.enrichment.search_snippets.map((snip, idx) => (
                  <li key={idx}>{snip}</li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
