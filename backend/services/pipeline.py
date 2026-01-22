from __future__ import annotations

from pathlib import Path
from typing import List
import json
import concurrent.futures

import numpy as np
import re
import string
from ..config import get_settings
from ..models import EnrichmentItem, GlobalNotes, SlideChunk, SlideEnrichment, TopicNote
from .embedding import embed_texts, embed_single
from .llm import LLMClient
from .parser import parse_ppt
from .search import search_arxiv, search_wikipedia, search_wikipedia_cn
from .vector_store import VectorStore


class PPTAgentPipeline:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.llm = LLMClient()
        # build a small dummy vector store; dimension will be filled after first embedding
        self.vector_store: VectorStore | None = None
        self.corpus: List[SlideChunk] = []
        self.embeddings: List[List[float]] = []
        self.slide_vectors: List[np.ndarray] = []
        self.cache_dir = settings.data_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_index(self, dim: int) -> None:
        if self.vector_store is None:
            self.vector_store = VectorStore(dim=dim, index_path=self.settings.faiss_path)

    def load_ppt(self, ppt_path: Path) -> List[SlideChunk]:
        slides = parse_ppt(ppt_path)
        self.corpus = slides
        texts = [slide.raw_text for slide in slides]
        embeddings = embed_texts(texts) if texts else []
        self.embeddings = embeddings
        self.slide_vectors = [np.array(e) for e in embeddings]
        if embeddings:
            self._ensure_index(len(embeddings[0]))
            self.vector_store.add(embeddings)
        return slides

    def _dedup_indices(self, threshold: float = 0.82) -> List[int]:
        """简单去重：找相似度高的 slides 只保留首个索引"""
        if not self.embeddings:
            return list(range(len(self.corpus)))
        kept: List[int] = []
        for i, emb in enumerate(self.embeddings):
            duplicate = False
            for k in kept:
                # embeddings 已归一化，点积即相似度
                sim = float(np.dot(np.array(emb), np.array(self.embeddings[k])))
                if sim >= threshold:
                    duplicate = True
                    break
            if not duplicate:
                kept.append(i)
        return kept

    def _retrieve_context(self, slide: SlideChunk, top_k: int) -> List[str]:
        if not self.vector_store:
            return []
        embedding = embed_single(slide.raw_text)
        neighbors = self.vector_store.search(embedding, k=top_k)
        context = []
        for idx, score in neighbors:
            if idx < len(self.corpus):
                neighbor = self.corpus[idx]
                context.append(f"相关页{neighbor.slide_number}({score:.2f}): {neighbor.raw_text}")
        return context

    def enrich_slide(self, slide: SlideChunk) -> SlideEnrichment:
        search_snippets = []
        if slide.title:
            search_snippets = (
                search_wikipedia(slide.title, limit=2)
                + search_wikipedia_cn(slide.title, limit=2)
                + search_arxiv(slide.title, limit=2)
            )
        context = self._retrieve_context(slide, top_k=self.settings.top_k)
        llm_reply = self.llm.expand_slide(slide.raw_text, search_snippets + context)
        enrichment = EnrichmentItem(
            summary=llm_reply.split("\n")[0] if llm_reply else "",
            expansions=[line for line in llm_reply.split("\n") if line.strip()],
            references=context,
            search_snippets=search_snippets,
        )
        return SlideEnrichment(
            slide_number=slide.slide_number,
            title=slide.title,
            raw_text=slide.raw_text,
            section=slide.section,
            enrichment=enrichment,
        )

    def run(self, ppt_path: Path):
        cached = self._load_cache(ppt_path)
        if cached:
            return cached, None

        slides = self.load_ppt(ppt_path)
        dedup_indices = set(self._dedup_indices())
        filtered: List[SlideChunk] = []
        for idx, slide in enumerate(slides):
            # 标题单页（只有标题或极少文字）直接跳过
            if slide.is_heading or (slide.title and not slide.raw_text.strip()):
                continue
            if slide.title and len(slide.raw_text.strip()) <= 30 and len(slide.raw_text.splitlines()) <= 1:
                continue
            # 目录页检测：标题含“目录”或正文大部分为编号条目
            if slide.title and "目录" in slide.title:
                continue
            lines = [ln.strip() for ln in slide.raw_text.splitlines() if ln.strip()]
            if lines:
                num_lines = sum(1 for ln in lines if re.match(r"^\d+[\.\u3001\)]", ln))
                if num_lines >= 2 and num_lines / len(lines) >= 0.6:
                    continue
            if idx not in dedup_indices:
                continue
            filtered.append(slide)

        topics = self._group_topics(filtered)
        topic_notes: List[TopicNote] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for idx, topic in enumerate(topics):
                futures.append((idx, executor.submit(self._enrich_topic, topic)))
            for idx, fut in futures:
                result = fut.result()
                if result:
                    topic_notes.append((idx, result))
        topic_notes = [r for _, r in sorted(topic_notes, key=lambda x: x[0])]

        # 全局概述移除，直接返回知识块
        self._save_cache(ppt_path, topic_notes)
        return topic_notes, None

    def _group_topics(self, slides: List[SlideChunk]) -> List[dict]:
        """按 PPT 顺序聚合：基于主/子标题合并同主题页面，正文页继承最近标题"""
        def norm_text(t: str | None) -> str:
            if not t:
                return ""
            t = t.lower()
            t = t.translate(str.maketrans("", "", string.punctuation))
            return re.sub(r"\s+", " ", t).strip()

        clusters: list[dict] = []
        index_map: dict[tuple[str, str], dict] = {}
        last_title = ""

        for slide in slides:
            # 跳过显式占位标题
            if slide.title and any(kw in slide.title for kw in ["目录", "目录页", "知识块", "知识 block", "标题"]):
                continue

            # 决定当前页的有效标题：有标题用标题；无标题继承上一标题；若仍为空，用章节名
            eff_title = slide.title.strip() if slide.title else ""

            # 若标题是步骤/编号开头（第1步、Step 1等），视为沿用上一小标题
            if eff_title and re.match(r"^(第\\s*\\d|step\\s*\\d)", eff_title, re.IGNORECASE):
                eff_title = last_title

            # 若标题过长（疑似正文首句），也归并到上一标题
            if eff_title and len(eff_title) > 60:
                eff_title = last_title

            if eff_title:
                last_title = eff_title
            else:
                eff_title = last_title or (slide.section or "").strip()
            if not eff_title:
                continue

            key_section = norm_text(slide.section)
            key_title = norm_text(eff_title)
            cluster_key = (key_section, key_title)

            if cluster_key in index_map:
                index_map[cluster_key]["slides"].append(slide)
            else:
                cluster = {
                    "section": slide.section,
                    "title": eff_title,
                    "slides": [slide],
                }
                index_map[cluster_key] = cluster
                clusters.append(cluster)

        merged_clusters: List[dict] = []
        for cluster in clusters:
            merged_texts = [s.raw_text for s in cluster["slides"] if s.raw_text]
            if not merged_texts:
                continue
            merged = SlideChunk(
                slide_number=min(s.slide_number for s in cluster["slides"]),
                title=cluster["title"],
                bullets=[],
                notes=None,
                raw_text="\n".join(merged_texts),
                section=cluster["section"],
                is_heading=False,
                level=cluster["slides"][0].level,
            )
            merged_clusters.append(
                {
                    "title": cluster["title"],
                    "slide_numbers": [s.slide_number for s in cluster["slides"]],
                    "section": cluster["section"],
                    "merged": merged,
                }
            )
        # 按首次出现的页码排序，保持原始目录顺序
        merged_clusters.sort(key=lambda c: c["merged"].slide_number)
        return merged_clusters

    def _enrich_topic(self, topic: dict) -> TopicNote | None:
        enriched = self.enrich_slide(topic["merged"])
        cleaned_expansions = []
        for line in enriched.enrichment.expansions:
            if not line:
                continue
            stripped = line.strip()
            if stripped.lower().startswith("1)") or stripped.lower().startswith("1."):
                continue
            if stripped.lower().startswith("概要"):
                continue
            if stripped == enriched.enrichment.summary.strip():
                continue
            cleaned_expansions.append(stripped)
        enriched.enrichment.expansions = cleaned_expansions[:]
        title_text = topic["title"] or ""
        if any(word in title_text for word in ["目录", "知识块"]):
            return None
        return TopicNote(
            title=topic["title"],
            slide_numbers=topic["slide_numbers"],
            section=topic["section"],
            raw_text=topic["merged"].raw_text,
            enrichment=enriched.enrichment,
        )

    def _cache_path(self, ppt_path: Path) -> Path:
        stat = ppt_path.stat()
        key = f"{ppt_path.stem}_{stat.st_mtime_ns}_{stat.st_size}.json"
        return self.cache_dir / key

    def _load_cache(self, ppt_path: Path):
        path = self._cache_path(ppt_path)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            topics = []
            for t in data.get("topics", []):
                topics.append(
                    TopicNote(
                        title=t.get("title"),
                        slide_numbers=t.get("slide_numbers", []),
                        section=t.get("section"),
                        raw_text=t.get("raw_text", ""),
                        enrichment=EnrichmentItem(
                            summary=t["enrichment"]["summary"],
                            expansions=t["enrichment"]["expansions"],
                            references=t["enrichment"].get("references", []),
                            search_snippets=t["enrichment"].get("search_snippets", []),
                        ),
                    )
                )
            return topics
        except Exception:
            return None

    def _save_cache(self, ppt_path: Path, topics: List[TopicNote]) -> None:
        path = self._cache_path(ppt_path)
        payload = {
            "topics": [
                {
                    "title": t.title,
                    "slide_numbers": t.slide_numbers,
                    "section": t.section,
                    "raw_text": t.raw_text,
                    "enrichment": {
                        "summary": t.enrichment.summary,
                        "expansions": t.enrichment.expansions,
                        "references": t.enrichment.references,
                        "search_snippets": t.enrichment.search_snippets,
                    },
                }
                for t in topics
            ]
        }
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
