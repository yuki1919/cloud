
# PPT 内容扩展智能体

面向“考前复习只有 PPT 标题”的痛点，提供一个能解析 PPT 结构、语义检索并用大模型自动补充背景/公式/代码示例的云原生方案。
后端基于 FastAPI + Docker。
解析用 `python-pptx`，向量由 `sentence-transformers` 生成，检索用 FAISS。
默认调用硅基流动的 `deepseek-ai/DeepSeek-V3.2`，无密钥则返回离线兜底。

## 目录结构
- `backend/`：FastAPI 后端（解析/检索/LLM）。
- `frontend/`：Next.js 14 前端（上传、折叠展示、导出）。
- `docker-compose.yml`：一键启动后端容器。

## 使用步骤（最短路径）
1) 后端环境：在 `backend/` 执行 `cp .env.example .env`，填入硅基流动 `OPENAI_API_KEY`，可改 `MODEL_NAME`/`LLM_BASE_URL`。
2) 启动后端（本地）：`python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt && uvicorn app:app --host 0.0.0.0 --port 8000`。
   或容器：在仓库根目录 `docker compose up --build`（映射 8000）。
3) 启动前端：进入 `frontend/`，`npm install && npm run dev`，访问 `http://localhost:3000`。
   如后端非本机，在 `frontend/.env` 设置 `NEXT_PUBLIC_API_BASE`（默认 `http://localhost:8000`）。
4) 使用：在前端上传 `.pptx`，等待处理后折叠查看每页扩展内容，可导出 Markdown/PDF。

## API 速览
- 健康检查：`GET /health`。
- PPT 扩写：`POST /ppt/process`，表单字段 `file` 上传 .pptx。

## 智能体与检索策略
解析：`parser.py` 提取页码、标题、要点、备注，形成 `SlideChunk`。
编排：`pipeline.py` 解析 → 句向量 → FAISS 近邻 → 多源检索 → LLM 扩写。
多源检索：英文/中文 Wikipedia + arXiv 学术摘要，拼接为提示上下文。
LLM：`llm.py` 调用 DeepSeek Chat Completions，输出“概要/要点/参考”三段式，无密钥走离线提示。

## 前端特性（frontend/）
- 上传 `.pptx` 后折叠展示每页：原文、概要、扩展要点。
- 展示检索片段与近邻参考。
- 导出：一键下载 Markdown / PDF（`lib/download.ts`）。
- 可通过 `NEXT_PUBLIC_API_BASE` 指定后端地址。

## 环境变量
- 后端：`OPENAI_API_KEY`（由于安全性考虑，提交后会删除相应的apikey）、`MODEL_NAME`、`LLM_BASE_URL`、`EMBEDDING_MODEL`、`DATA_DIR`、`FAISS_PATH`、`TOP_K`。
- 前端：`NEXT_PUBLIC_API_BASE`（默认 `http://localhost:8000`）。

## 参考命令
- 单测接口：`curl -F "file=@sample.pptx" http://localhost:8000/ppt/process`。
- 查看索引：`ls backend/data`，删除即可重建。
