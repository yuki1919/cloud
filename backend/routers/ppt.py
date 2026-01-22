from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
import requests

from ..models import ProcessResponse
from ..services.pipeline import PPTAgentPipeline

router = APIRouter(prefix="/ppt", tags=["ppt"])


@router.post("/process", response_model=ProcessResponse)
async def process_ppt(
    file: UploadFile | None = File(None),
    url: str | None = Form(None),
) -> ProcessResponse:
    if not file and not url:
        raise HTTPException(status_code=400, detail="file 或 url 至少提供一个")

    if file:
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_path = Path(tmp.name)
    else:
        try:
            resp = requests.get(url, timeout=30, allow_redirects=True)
            resp.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"下载 URL 失败: {e}")
        content = resp.content
        if not content:
            raise HTTPException(status_code=400, detail="URL 返回空文件")
        # 如果返回 HTML，提前提示（但可根据需要注释掉以继续尝试解析）
        snippet = content[:200].lower()
        if snippet.startswith(b"<!doctype") or snippet.startswith(b"<html"):
            raise HTTPException(status_code=400, detail="URL 未返回 PPT 文件（检测到 HTML）")
        # 根据 URL 或 Content-Type 猜后缀
        suffix = Path(url).suffix.lower() or ""
        if suffix not in {".ppt", ".pptx"}:
            ctype = resp.headers.get("Content-Type", "").lower()
            if "ppt" in ctype:
                suffix = ".pptx" if "pptx" in ctype else ".ppt"
            else:
                suffix = ".pptx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            temp_path = Path(tmp.name)

    pipeline = PPTAgentPipeline()
    topics, global_notes = pipeline.run(temp_path)
    return ProcessResponse(slides=[], topics=topics, global_notes=global_notes)
