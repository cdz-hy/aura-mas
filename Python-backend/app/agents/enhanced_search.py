"""
增强版 ReAct 搜索引擎 - 支持自主多轮搜索和网页提取
"""
import logging
import concurrent.futures
import hashlib
import requests
from typing import Dict, List, Literal, Optional
from app.core.config import settings

logger = logging.getLogger("agents.enhanced_search")


def validate_image_url(url: str, timeout: int = 3) -> bool:
    """
    验证图片 URL 是否有效（快速 HEAD 请求）

    Args:
        url: 图片 URL
        timeout: 超时时间（秒）

    Returns:
        True 如果图片可访问，False 否则
    """
    try:
        # 使用 HEAD 请求减少流量
        response = requests.head(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )

        # 检查状态码
        if response.status_code != 200:
            return False

        # 检查 Content-Type 是否为图片
        content_type = response.headers.get('Content-Type', '').lower()
        if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'png', 'gif', 'webp', 'svg']):
            return False

        return True
    except Exception as e:
        logger.debug(f"  [ImageValidation] Failed to validate {url}: {str(e)[:80]}")
        return False


def batch_validate_images(images: List[Dict[str, str]], max_workers: int = 5) -> List[Dict[str, str]]:
    """
    批量验证图片 URL，过滤掉无效的

    Args:
        images: 图片列表 [{"url": "...", "description": "..."}]
        max_workers: 并发验证线程数

    Returns:
        验证通过的图片列表
    """
    if not images:
        return []

    valid_images = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交验证任务
        future_to_image = {
            executor.submit(validate_image_url, img.get("url", "")): img
            for img in images if img.get("url")
        }

        # 收集验证结果
        for future in concurrent.futures.as_completed(future_to_image):
            img = future_to_image[future]
            try:
                is_valid = future.result(timeout=5)
                if is_valid:
                    valid_images.append(img)
            except Exception as e:
                logger.debug(f"  [ImageValidation] Exception for {img.get('url', '')[:50]}: {str(e)[:50]}")

    logger.info(f"  [ImageValidation] {len(valid_images)}/{len(images)} images valid")
    return valid_images


def search_web(query: str, max_results: int = 5) -> Dict:
    """
    Tavily 网页搜索

    Args:
        query: 搜索关键词
        max_results: 返回结果数量

    Returns:
        {
            "results": [{"title": str, "snippet": str, "url": str, "score": float}],
            "images": [{"url": str, "description": str}]
        }
    """
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        resp = client.search(
            query,
            max_results=max_results,
            include_images=True,
            include_image_descriptions=True,
            search_depth="advanced"  # 使用高级搜索获得更详细结果
        )

        results = []
        for r in resp.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("content", ""),
                "url": r.get("url", ""),
                "score": r.get("score", 0.0)
            })

        images = []
        seen_img_urls = set()

        # 顶层图片
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

        # 结果中的图片
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

        # 验证图片 URL 有效性（过滤 404）
        if images:
            images = batch_validate_images(images, max_workers=5)

        logger.info(f"  [Search] '{query}' -> {len(results)} results, {len(images)} images (validated)")
        return {
            "results": results,
            "images": images,
            "query": query
        }
    except Exception as e:
        logger.warning(f"  [Search] Failed '{query}': {str(e)[:120]}")
        return {"results": [], "images": [], "query": query, "error": str(e)}


def extract_webpage(url: str) -> Dict:
    """
    提取网页完整内容

    Args:
        url: 网页 URL

    Returns:
        {
            "url": str,
            "content": str,  # 完整网页文本内容
            "title": str,
            "success": bool
        }
    """
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)

        # Tavily 的 extract 方法
        resp = client.extract(urls=[url])

        if resp and "results" in resp and len(resp["results"]) > 0:
            result = resp["results"][0]
            content = result.get("raw_content", "")
            title = result.get("title", "")

            logger.info(f"  [Extract] {url} -> {len(content)} chars")
            return {
                "url": url,
                "content": content,
                "title": title,
                "success": True
            }
        else:
            logger.warning(f"  [Extract] No content from {url}")
            return {
                "url": url,
                "content": "",
                "title": "",
                "success": False,
                "error": "No content returned"
            }
    except Exception as e:
        logger.warning(f"  [Extract] Failed {url}: {str(e)[:120]}")
        return {
            "url": url,
            "content": "",
            "title": "",
            "success": False,
            "error": str(e)
        }


def execute_actions_parallel(actions: List[Dict]) -> List[Dict]:
    """
    并行执行多个搜索/提取动作

    Args:
        actions: [
            {"action": "search", "query": "...", "max_results": 5},
            {"action": "extract", "url": "..."}
        ]

    Returns:
        结果列表，顺序与输入一致
    """
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []

        for action in actions:
            action_type = action.get("action", "")

            if action_type == "search":
                query = action.get("query", "")
                max_results = action.get("max_results", 5)
                if query:
                    future = executor.submit(search_web, query, max_results)
                    futures.append(("search", future, action))

            elif action_type == "extract":
                url = action.get("url", "")
                if url:
                    future = executor.submit(extract_webpage, url)
                    futures.append(("extract", future, action))

        for action_type, future, original_action in futures:
            try:
                result = future.result(timeout=30)
                result["action_type"] = action_type
                result["original_action"] = original_action
                results.append(result)
            except Exception as e:
                logger.warning(f"  [Parallel] {action_type} failed: {str(e)[:120]}")
                results.append({
                    "action_type": action_type,
                    "original_action": original_action,
                    "error": str(e),
                    "success": False
                })

    return results


class SearchHistoryTracker:
    """搜索历史追踪器 - 用摘要而非全文避免 prompt 膨胀"""

    def __init__(self):
        self.search_history: List[Dict] = []  # 搜索历史摘要
        self.extracted_pages: Dict[str, str] = {}  # URL -> 完整内容
        self.all_snippets: List[Dict] = []  # 所有搜索结果片段
        self.all_images: List[Dict] = []  # 所有图片
        self.seen_urls: set = set()
        self.seen_img_urls: set = set()

    def add_search_result(self, query: str, results: List[Dict], images: List[Dict]):
        """记录搜索结果"""
        # 去重并添加片段
        new_snippets = []
        for r in results:
            url = r.get("url", "")
            if url and url not in self.seen_urls:
                self.seen_urls.add(url)
                self.all_snippets.append(r)
                new_snippets.append(r)

        # 去重并添加图片
        new_images = []
        for img in images:
            img_url = img.get("url", "")
            if img_url and img_url not in self.seen_img_urls:
                self.seen_img_urls.add(img_url)
                self.all_images.append(img)
                new_images.append(img)

        # 记录到历史（仅摘要）
        self.search_history.append({
            "round": len(self.search_history) + 1,
            "action": "search",
            "query": query,
            "new_results_count": len(new_snippets),
            "total_results_count": len(self.all_snippets)
        })

        logger.info(f"  [History] Search '{query}' -> +{len(new_snippets)} new ({len(self.all_snippets)} total)")

    def add_extracted_page(self, url: str, title: str, content: str):
        """记录提取的完整网页"""
        if url not in self.extracted_pages:
            self.extracted_pages[url] = content
            self.search_history.append({
                "round": len(self.search_history) + 1,
                "action": "extract",
                "url": url,
                "title": title,
                "content_length": len(content)
            })
            logger.info(f"  [History] Extract {url} -> {len(content)} chars")

    def get_summary_for_llm(self, max_recent_snippets: int = 20) -> str:
        """
        生成给 LLM 的摘要（避免 prompt 膨胀）

        策略：
        - 历史动作：显示所有轮次的简要信息
        - 搜索片段：只显示最近的 N 条
        - 提取网页：显示 URL 和长度，不显示全文（LLM 需要时可以从 extracted_pages 获取）
        """
        lines = []

        # 1. 历史动作摘要
        lines.append("## 已执行的搜索动作")
        for h in self.search_history:
            if h["action"] == "search":
                lines.append(f"- 第 {h['round']} 轮：搜索 '{h['query']}' (+{h['new_results_count']} 条新结果)")
            elif h["action"] == "extract":
                lines.append(f"- 第 {h['round']} 轮：提取网页 {h['url']} ({h['content_length']} 字)")

        # 2. 统计信息
        lines.append(f"\n## 当前资源统计")
        lines.append(f"- 搜索结果片段：{len(self.all_snippets)} 条")
        lines.append(f"- 提取完整网页：{len(self.extracted_pages)} 个")
        lines.append(f"- 可用图片：{len(self.all_images)} 张")

        # 3. 最近的搜索片段（避免全部显示）
        if self.all_snippets:
            recent_snippets = self.all_snippets[-max_recent_snippets:]
            lines.append(f"\n## 最近的搜索结果片段（最新 {len(recent_snippets)} 条）")
            for i, snippet in enumerate(recent_snippets):
                idx = len(self.all_snippets) - len(recent_snippets) + i + 1
                lines.append(f"[{idx}] {snippet.get('title', '无标题')}")
                lines.append(f"    {snippet.get('snippet', '')[:150]}...")
                lines.append(f"    URL: {snippet.get('url', '')}")

        # 4. 提取的网页列表（不含全文）
        if self.extracted_pages:
            lines.append(f"\n## 已提取的完整网页")
            for i, (url, content) in enumerate(self.extracted_pages.items(), 1):
                lines.append(f"[page{i}] {url} ({len(content)} 字)")

        return "\n".join(lines)

    def get_all_content_for_generation(self) -> Dict:
        """获取所有内容用于最终生成"""
        return {
            "snippets": self.all_snippets,
            "extracted_pages": self.extracted_pages,
            "images": self.all_images
        }


def format_action_results_for_llm(results: List[Dict]) -> str:
    """格式化本轮动作执行结果给 LLM 观察"""
    lines = []

    for i, result in enumerate(results, 1):
        action_type = result.get("action_type", "")

        if action_type == "search":
            query = result.get("query", "")
            search_results = result.get("results", [])
            images = result.get("images", [])

            lines.append(f"### 动作 {i}: 搜索 '{query}'")
            if "error" in result:
                lines.append(f"❌ 失败: {result['error']}")
            else:
                lines.append(f"✓ 找到 {len(search_results)} 条结果, {len(images)} 张图片")
                for j, r in enumerate(search_results[:5], 1):  # 只显示前5条
                    lines.append(f"  [{j}] {r.get('title', '无标题')}")
                    lines.append(f"      {r.get('snippet', '')[:120]}...")
                    lines.append(f"      {r.get('url', '')}")

        elif action_type == "extract":
            url = result.get("url", "")
            title = result.get("title", "")
            content = result.get("content", "")
            success = result.get("success", False)

            lines.append(f"### 动作 {i}: 提取网页 {url}")
            if success:
                lines.append(f"✓ 成功提取 {len(content)} 字")
                lines.append(f"  标题: {title}")
                lines.append(f"  预览: {content[:200]}...")
            else:
                lines.append(f"❌ 失败: {result.get('error', 'Unknown error')}")

    return "\n".join(lines)
