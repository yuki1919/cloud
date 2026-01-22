from __future__ import annotations

from typing import List

import feedparser

import requests


def search_wikipedia(query: str, limit: int = 3) -> List[str]:
    params = {
        "action": "query",
        "list": "search",
        "format": "json",
        "srsearch": query,
        "srlimit": limit,
    }
    try:
        resp = requests.get("https://en.wikipedia.org/w/api.php", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("query", {}).get("search", [])
        snippets = []
        for item in results:
            title = item.get("title")
            snippet = item.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")
            snippets.append(f"{title}: {snippet}")
        return snippets
    except Exception:
        return []


def search_wikipedia_cn(query: str, limit: int = 3) -> List[str]:
    params = {
        "action": "query",
        "list": "search",
        "format": "json",
        "srsearch": query,
        "srlimit": limit,
    }
    try:
        resp = requests.get("https://zh.wikipedia.org/w/api.php", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("query", {}).get("search", [])
        snippets = []
        for item in results:
            title = item.get("title")
            snippet = item.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", "")
            snippets.append(f"{title}: {snippet}")
        return snippets
    except Exception:
        return []


def search_arxiv(query: str, limit: int = 3) -> List[str]:
    api_url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={limit}"
    try:
        feed = feedparser.parse(api_url)
        results = []
        for entry in feed.entries[:limit]:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "")
            summary = getattr(entry, "summary", "").strip().replace("\n", " ")
            results.append(f"{title} | {link} | {summary[:160]}...")
        return results
    except Exception:
        return []
