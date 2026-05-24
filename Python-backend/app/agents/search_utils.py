"""
网络搜索工具模块 - 供 resource_generator 和 tutor_agent 共同使用
"""
import logging
import concurrent.futures
from typing import Dict, List
from app.core.config import settings

logger = logging.getLogger("agents.search_utils")


def search_tavily(query: str, max_results: int = 5) -> tuple:
    """Tavily 网页搜索，返回 (文本结果列表, 图片URL列表)"""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        resp = client.search(query, max_results=max_results, include_images=True, include_image_descriptions=True)
        results = []
        for r in resp.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("content") or "",
                "url": r.get("url", ""),
            })
        images = []
        seen_img_urls = set()
        for img in resp.get("images", []):
            if isinstance(img, dict):
                img_url = img.get("url", "")
                img_desc = img.get("description", "")
            else:
                img_url = str(img)
                img_desc = ""
            if img_url and img_url not in seen_img_urls:
                seen_img_urls.add(img_url)
                images.append({"url": img_url, "description": img_desc})
        for r in resp.get("results", []):
            for img in r.get("images", []):
                if isinstance(img, dict):
                    img_url = img.get("url", "")
                    img_desc = img.get("description", "")
                else:
                    img_url = str(img)
                    img_desc = ""
                if img_url and img_url not in seen_img_urls:
                    seen_img_urls.add(img_url)
                    images.append({"url": img_url, "description": img_desc})
        logger.info(f"  [Tavily] '{query}' -> {len(results)} 条文本, {len(images)} 张图片")
        return results, images
    except Exception as e:
        logger.warning(f"  [Tavily] 搜索失败 '{query}': {str(e)[:120]}")
        return [], []


def execute_searches(queries: List[str]) -> tuple:
    """并行执行所有搜索查询，返回 (去重后的文本结果列表, 去重后的图片列表)"""
    all_results: List[Dict[str, str]] = []
    all_images: List[Dict[str, str]] = []
    seen_urls: set = set()
    seen_img_urls: set = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(search_tavily, q): q for q in queries}
        for future in concurrent.futures.as_completed(futures):
            try:
                items, images = future.result()
                for item in items:
                    url = item.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(item)
                for img in images:
                    img_url = img.get("url", "")
                    if img_url and img_url not in seen_img_urls:
                        seen_img_urls.add(img_url)
                        all_images.append(img)
            except Exception as e:
                logger.warning(f"  [搜索] 任务执行异常: {str(e)[:120]}")

    return all_results, all_images


def format_search_results(results: List[Dict[str, str]]) -> str:
    """格式化搜索结果为 LLM 可读文本"""
    lines = []
    for i, r in enumerate(results):
        title = r.get("title", "无标题")
        snippet = r.get("snippet", "")
        url = r.get("url", "")
        line = f"[{i + 1}] {title}\n    {snippet}"
        if url:
            line += f"\n    来源: {url}"
        lines.append(line)
    return "\n".join(lines)
