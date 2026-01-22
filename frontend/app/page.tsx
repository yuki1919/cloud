"use client";

import axios from "axios";
import { useMemo, useState } from "react";
import { downloadMarkdown, downloadPDF } from "../lib/download";
import { SlideCard } from "../components/SlideCard";
import type { GlobalNotes, TopicNote } from "../types/slide";

type State = "idle" | "uploading" | "processing" | "done" | "error";

export default function Page() {
  const [topics, setTopics] = useState<TopicNote[]>([]);
  const [globalNotes, setGlobalNotes] = useState<GlobalNotes | null>(null);
  const [status, setStatus] = useState<State>("idle");
  const [message, setMessage] = useState<string>("");
  const [url, setUrl] = useState<string>("");
  // 使用同一值进行 SSR 与 CSR，避免 hydration mismatch
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  const handleUpload = async (evt: React.FormEvent<HTMLFormElement>) => {
    evt.preventDefault();
    const form = evt.currentTarget;
    const fileInput = form.elements.namedItem("file") as HTMLInputElement;
    const urlInput = url.trim();
    if (!fileInput.files?.length && !urlInput) {
      setMessage("请选择一个 PPTX 文件或填写云端 URL");
      return;
    }

    const formData = new FormData();
    if (fileInput.files?.length) {
      formData.append("file", fileInput.files[0]);
    }
    if (urlInput) {
      formData.append("url", urlInput);
    }

    try {
      setStatus("processing");
      setMessage("正在上传/拉取并扩写，请稍候...");
      const resp = await axios.post(`${apiBase}/ppt/process`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setTopics(resp.data.topics || []);
      setGlobalNotes(resp.data.global_notes || null);
      setStatus("done");
      setMessage(`完成，共 ${resp.data.topics?.length || 0} 个知识块`);
    } catch (err: any) {
      console.error(err);
      setStatus("error");
      setMessage("处理失败，请检查后端是否启动，或查看控制台日志。");
    }
  };

  const toolbarDisabled = useMemo(() => topics.length === 0, [topics]);

  return (
    <main>
      <h1>PPT 内容扩展智能体</h1>
      <p>解析 PPT，自动生成结构化复习笔记，支持折叠浏览与 Markdown / PDF 导出。</p>

      <div className="panel">
        <form onSubmit={handleUpload}>
          <div className="input-row">
            <label>选择 PPTX 文件</label>
            <input type="file" name="file" accept=".ppt,.pptx" />
          </div>
          <div className="input-row">
            <label>或输入云端 URL</label>
            <input
              type="url"
              placeholder="https://example.com/sample.pptx"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </div>
          <div className="toolbar">
            <button type="submit">{status === "processing" ? "处理中..." : "上传并扩写"}</button>
            <div className="pill">
              状态：
              <span className="status">
                {status === "idle" && "待上传"}
                {status === "processing" && "处理中"}
                {status === "done" && "完成"}
                {status === "error" && "错误"}
              </span>
            </div>
            <span>{message}</span>
          </div>
        </form>
        <p className="muted">
          后端地址：{apiBase}
        </p>
      </div>

      <div className="toolbar">
        <button className="secondary" onClick={() => downloadMarkdown(topics)} disabled={toolbarDisabled}>
          下载 Markdown
        </button>
        <button className="secondary" onClick={() => downloadPDF(topics)} disabled={toolbarDisabled}>
          下载 PDF
        </button>
      </div>

      <div className="grid">
        {topics.map((topic, idx) => (
          <SlideCard
            key={`${topic.title}-${idx}`}
            slide={{
              slide_number: idx + 1,
              title: topic.title,
              raw_text: topic.raw_text,
              section: topic.section,
              enrichment: topic.enrichment,
            }}
          />
        ))}
      </div>
    </main>
  );
}
