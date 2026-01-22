from __future__ import annotations

from typing import List, Optional

import requests

from ..config import get_settings


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.model_name = model_name or settings.model_name
        self.base_url = base_url or settings.llm_base_url

    def _fallback(self, prompt: str) -> str:
        head = prompt[:128].replace("\n", " ")
        return f"[离线模式] 无法访问LLM。请检查OPENAI_API_KEY。提示摘要: {head}"

    def complete(self, prompt: str) -> str:
        if not self.api_key:
            return self._fallback(prompt)
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个教学助理，请用简洁的方式补充背景、公式与示例。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.4,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return self._fallback(prompt)

    def expand_slide(self, slide_text: str, search_snippets: List[str]) -> str:
        prompt = (
            "下面是PPT页内容，请补充背景、推导或代码示例，并指出应补充的参考链接。"
            "要求结构化输出：1)概要；2)加深理解的要点列表；3)推荐阅读。"
            f"\n\nPPT内容：\n{slide_text}\n\n检索片段：\n"
            + "\n".join(search_snippets)
        )
        return self.complete(prompt)

    def summarize_global(self, outline: str, topics: str) -> str:
        prompt = (
            "根据以下 PPT 大纲与主题文本，生成一份整体复习笔记：\n"
            "1) 课程/汇报概要（3-5 句）；\n"
            "2) 核心知识点列表，每条尽量带公式/原理/代码要点；\n"
            "3) 关联/延伸参考建议。\n"
            "输出用清晰分段的 Markdown。\n\n"
            f"大纲：\n{outline}\n\n主题摘录：\n{topics}"
        )
        return self.complete(prompt)
