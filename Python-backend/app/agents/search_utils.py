"""
网络搜索工具模块 - 供 resource_generator 和 tutor_agent 共同使用
"""
import logging
import concurrent.futures
import io
import requests
from typing import Dict, List, Optional
from app.core.config import settings

# 全局共享的 requests.Session，配置连接池复用，解决高并发端口耗尽问题
_search_session = requests.Session()
_adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=50)
_search_session.mount('https://', _adapter)
_search_session.mount('http://', _adapter)

logger = logging.getLogger("agents.search_utils")


def validate_image_url(url: str, timeout: int = 5) -> bool:
    """验证图片 URL 是否有效（GET stream + 魔术字节校验）"""
    if not url or not url.startswith("http"):
        return False
    try:
        resp = _search_session.get(
            url, timeout=timeout, allow_redirects=True, stream=True,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                     'Accept': 'image/*,*/*'}
        )
        if resp.status_code >= 400:
            resp.close()
            return False

        content_type = resp.headers.get('Content-Type', '').lower()
        is_image_type = any(t in content_type for t in [
            'image/', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'tiff',
            'application/octet-stream'
        ])

        content_length = resp.headers.get('Content-Length')
        if content_length and int(content_length) < 100:
            resp.close()
            return False

        is_real_image = False
        try:
            header = resp.raw.read(16)
            if header:
                if header[:4] == b'\x89PNG':
                    is_real_image = True
                elif header[:3] == b'\xff\xd8\xff':
                    is_real_image = True
                elif header[:3] == b'GIF':
                    is_real_image = True
                elif header[:4] == b'RIFF' and len(header) >= 12 and header[8:12] == b'WEBP':
                    is_real_image = True
                elif header[:2] == b'BM':
                    is_real_image = True
                elif b'<svg' in header or b'<?xml' in header:
                    is_real_image = True
        except Exception:
            is_real_image = is_image_type

        resp.close()
        return is_real_image or is_image_type
    except Exception:
        return False


def download_image(url: str, timeout: int = 10, max_size_mb: int = 5) -> Optional[io.BytesIO]:
    """下载图片到内存 BytesIO，返回 BytesIO 对象或 None（失败/超限时）"""
    if not url or not url.startswith("http"):
        return None
    try:
        resp = _search_session.get(
            url, timeout=timeout, allow_redirects=True, stream=True,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                     'Accept': 'image/*,*/*'}
        )
        if resp.status_code >= 400:
            resp.close()
            return None

        content_type = resp.headers.get('Content-Type', '').lower()
        is_image = any(t in content_type for t in [
            'image/', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp',
            'application/octet-stream'
        ])
        if not is_image:
            resp.close()
            return None

        # 流式读取，限制最大文件大小
        max_bytes = max_size_mb * 1024 * 1024
        buf = io.BytesIO()
        downloaded = 0
        for chunk in resp.iter_content(chunk_size=8192):
            downloaded += len(chunk)
            if downloaded > max_bytes:
                resp.close()
                return None
            buf.write(chunk)
        resp.close()

        if buf.tell() < 100:
            return None

        buf.seek(0)
        return buf
    except Exception:
        return None


def batch_validate_images(images: List[Dict[str, str]], max_workers: int = 8) -> List[Dict[str, str]]:
    """批量验证图片 URL，过滤掉无效的"""
    if not images:
        return []

    seen = set()
    unique_images = []
    for img in images:
        url = img.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique_images.append(img)

    valid_images = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_image = {
            executor.submit(validate_image_url, img.get("url", "")): img
            for img in unique_images
        }
        for future in concurrent.futures.as_completed(future_to_image):
            img = future_to_image[future]
            try:
                if future.result(timeout=8):
                    valid_images.append(img)
            except Exception:
                pass

    logger.info(f"  [ImageValidation] {len(valid_images)}/{len(unique_images)} images valid")
    return valid_images


def search_tavily(query: str, max_results: int = 5, validate_images: bool = True) -> tuple:
    """Tavily 网页搜索，返回 (文本结果列表, 图片URL列表)
    validate_images: 是否验证图片有效性，视频搜索等不需要图片的场景可设为 False
    """
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

        # 验证图片 URL 有效性（过滤 404），视频搜索等场景可跳过
        if images and validate_images:
            images = batch_validate_images(images, max_workers=5)

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
    return "\n".join(lines)

def search_bilibili_videos(keyword: str) -> list:
    """B站原生搜索工具 (利用 bilibili-api-python)"""
    try:
        from bilibili_api import search, sync
    except ImportError:
        logger.warning("[Bilibili搜索] 未安装 bilibili-api-python，请执行 pip install bilibili-api-python")
        return []

    try:
        logger.info(f"  [Bilibili] 原生搜索: '{keyword}'")
        result = sync(search.search_by_type(
            keyword=keyword,
            search_type=search.SearchObjectType.VIDEO,
            page=1
        ))

        videos = []
        for item in result.get('result', []):
            title = item.get('title', '').replace('<em class="keyword">', '').replace('</em>', '')
            videos.append({
                "title": title,
                "bvid": item.get('bvid'),
                "author": item.get('author'),
                "url": f"https://www.bilibili.com/video/{item.get('bvid')}",
                "duration": item.get('duration'), # 格式如 10:23
                "platform": "Bilibili",
                "snippet": f"UP主: {item.get('author')} | 时长: {item.get('duration')}"
            })

        logger.info(f"  [Bilibili] 找到 {len(videos)} 个视频")
        return videos[:5]
    except Exception as e:
        logger.warning(f"  [Bilibili] 原生搜索失败 '{keyword}': {e}")
        return []
