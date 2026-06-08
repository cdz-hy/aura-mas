import logging
import json
import concurrent.futures
from typing import Dict, Any, List

from app.agents.llm_factory import get_video_search_llm
from app.agents.search_utils import search_tavily, search_bilibili_videos

logger = logging.getLogger("agents.video_search")

VIDEO_SEARCH_PROMPT = """你是一个专业的教学视频搜索专家。
你的目标是根据用户提供的模块标题和相关知识点详情，在网上检索并筛选出相关的高质量教学视频。

你现在可以自主决定使用以下工具：
- `search_bilibili`: B站原生精准搜索，适合搜索中文技术教程、考研、科普视频。输入 `keyword`。
- `search_tavily_cn`: 网页泛搜（中文），适合查找网易公开课、慕课网等其他平台的视频。输入 `query`（建议带上"教学视频"等字眼）。
- `search_tavily_en`: 网页泛搜（英文），适合查找 YouTube, Coursera 等前沿技术视频。输入 `query`（建议带上"tutorial video"等字眼）。

## 当前任务上下文
模块标题: {module_title}
知识点详情:
{source_resource_content}

## 历史搜索结果摘要
{history_summary}

你有最多 {max_rounds} 轮搜索机会。当前是第 {current_round} 轮。
每轮你可以并行调用多个工具（推荐同时搜 B 站和英文）。
你可以通过分析当前已知结果，决定：
1. 继续搜索 (action: "search_xxx")：如果觉得还需要更多视角或找不到好视频，就换关键词继续搜。
2. 结束搜索 (decision: "finish")：如果你已经收集到了足够多、足够好的视频候选（收集够了就可以结束，后续会统一进行打分排序）。

【重要规则】
- **必须紧贴任务上下文的特定背景！**不要只搜空泛的词汇。提取搜索词时，必须结合上下文中的具体实体或限制条件。例如：如果上下文是关于“南昌航空大学软件学院”的介绍，你的搜索词必须是“南昌航空大学软件学院”，**绝不能**只搜泛泛的“软件学院”。
- **提取具体实体名作为搜索词：** 从上下文中提取人名、UP主名、频道名、课程名、技术术语等具体实体。例如上下文提到“UP主永雏塔菲”，搜索词应该是“永雏塔菲”而非泛泛的“视频博主分析”。
- `search_bilibili` 只需要传核心关键词（如 "南昌航空大学软件学院" 或 "Python 装饰器"），不要带"教学视频"等冗余词。
- `search_tavily_cn/en` 必须在关键词里带上 "视频" / "video" 才能确保搜出来的是视频。

请严格返回以下 JSON 格式：
```json
{{
  "thought": "你的思考过程...",
  "decision": "continue", // "continue" 或 "finish"
  "actions": [ // 如果 decision="continue"，必须提供至少一个 action
    {{"action": "search_bilibili", "keyword": "Python 装饰器"}},
    {{"action": "search_tavily_en", "query": "Python decorator tutorial video"}}
  ]
}}
```
"""

FINAL_SCREENING_PROMPT = """你是一个专业的教学视频审查与排序专家。
经过前期的搜索，我们收集到了以下候选视频列表。
请根据用户的模块标题和知识点详情，对这些视频进行严格筛选和排序。

## 任务上下文
模块标题: {module_title}
知识点详情:
{source_resource_content}

## 候选视频列表
```json
{candidates_json}
```

【审查与筛选规则】
1. **相关性第一**：仔细比对视频内容（标题和简介）与任务上下文，剔除明显偏题、与上下文无关或太泛泛而谈的视频。
2. **宁缺毋滥**：只保留高质量且切题的视频。数量由你决定，最多不超过 10 个（可以是 3 个、5 个，如果没有合适的甚至可以返回空列表）。
3. **最优排序**：将最权威、最相关、质量最高的视频排在前面。

请严格返回以下 JSON 格式，必须保留所选视频原有的完整结构（title, url, platform, snippet）：
```json
{{
  "thought": "你的筛选与排序理由...",
  "videos": [
    {{
      "title": "视频标题",
      "url": "视频播放链接",
      "platform": "平台名称",
      "snippet": "简介"
    }}
  ]
}}
```
"""

def _parse_tavily_video_results(results: list) -> list:
    """复用旧逻辑从 Tavily 结果中过滤视频"""
    video_domains = [
        "youtube.com", "youtu.be", "bilibili.com", "b23.tv",
        "v.qq.com", "iqiyi.com", "youku.com", "vimeo.com",
        "ted.com", "coursera.org", "edx.org", "mooc.cn",
    ]
    seen_urls = set()
    videos = []
    for r in results:
        url = r.get("url", "")
        if not url or url in seen_urls:
            continue
        domain_match = any(d in url.lower() for d in video_domains)
        title_match = any(k in r.get("title", "").lower() for k in ["视频", "video", "教程", "tutorial", "讲座", "课程"])
        if domain_match or title_match:
            seen_urls.add(url)
            platform = "其他"
            if "youtube.com" in url or "youtu.be" in url:
                platform = "YouTube"
            elif "bilibili.com" in url or "b23.tv" in url:
                platform = "Bilibili"
            elif "v.qq.com" in url:
                platform = "腾讯视频"
            elif "iqiyi.com" in url:
                platform = "爱奇艺"
            elif "youku.com" in url:
                platform = "优酷"
            elif "vimeo.com" in url:
                platform = "Vimeo"
            elif "ted.com" in url:
                platform = "TED"
            elif "coursera.org" in url:
                platform = "Coursera"
            elif "edx.org" in url:
                platform = "edX"
            videos.append({
                "title": r.get("title", ""),
                "url": url,
                "snippet": r.get("snippet", ""),
                "platform": platform,
            })
    return videos

def search_videos_with_agent(module_title: str, source_resource_content: str, sse_callback=None) -> list:
    """使用自主智能体搜索视频"""
    llm = get_video_search_llm()
    MAX_ROUNDS = 3
    
    all_found_videos = []
    history_lines = []
    seen_urls = set()
    
    # 阶段一：ReAct 多轮自主检索
    for round_num in range(1, MAX_ROUNDS + 1):
        if sse_callback:
            sse_callback(f'data: {json.dumps({"type": "progress", "content": f"正在进行第 {round_num}/{MAX_ROUNDS} 轮检索..."}, ensure_ascii=False)}\n\n')
            
        history_summary = "暂无"
        if history_lines:
            history_summary = "之前搜集到的相关视频候选：\n" + "\n".join(history_lines)
            
        prompt = VIDEO_SEARCH_PROMPT.format(
            module_title=module_title,
            source_resource_content=source_resource_content[:3000] if source_resource_content else "无详细内容",
            history_summary=history_summary,
            max_rounds=MAX_ROUNDS,
            current_round=round_num
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        try:
            result = llm.chat_json(messages)
            logger.info(f"  [VideoSearchAgent] 第 {round_num} 轮思考: {result.get('thought', '')}")
            decision = result.get("decision", "finish")
            
            if decision == "finish" or round_num == MAX_ROUNDS:
                logger.info(f"  [VideoSearchAgent] 搜索阶段结束，共有 {len(all_found_videos)} 个候选")
                break
            
            actions = result.get("actions", [])
            if not actions:
                logger.info("  [VideoSearchAgent] 无动作，搜索阶段结束")
                break
                
            # 执行工具
            new_videos = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = {}
                for action in actions:
                    act_type = action.get("action")
                    if act_type == "search_bilibili":
                        kw = action.get("keyword", module_title)
                        futures[executor.submit(search_bilibili_videos, kw)] = "bilibili"
                    elif act_type == "search_tavily_cn":
                        q = action.get("query", module_title)
                        futures[executor.submit(search_tavily, q, 5, False)] = "tavily"
                    elif act_type == "search_tavily_en":
                        q = action.get("query", module_title)
                        futures[executor.submit(search_tavily, q, 3, False)] = "tavily"
                        
                for future in concurrent.futures.as_completed(futures):
                    try:
                        res = future.result()
                        source = futures[future]
                        if source == "bilibili":
                            new_videos.extend(res)
                        else:
                            # res is (results, images)
                            items, _ = res
                            parsed = _parse_tavily_video_results(items)
                            new_videos.extend(parsed)
                    except Exception as e:
                        logger.warning(f"  [VideoSearchAgent] 工具执行异常: {e}")
            
            # 加入历史
            for v in new_videos:
                url = v.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_found_videos.append(v)
                    history_lines.append(f"- [{v.get('platform')}] {v.get('title')} ({url})")
                    
        except Exception as e:
            logger.warning(f"  [VideoSearchAgent] LLM 调用异常: {e}")
            break

    # 阶段二：大模型最终筛选与排序
    if not all_found_videos:
        logger.info("  [VideoSearchAgent] 最终没有找到任何视频候选")
        return []

    if sse_callback:
        sse_callback(f'data: {json.dumps({"type": "progress", "content": f"搜索完毕，正在对 {len(all_found_videos)} 个候选视频进行最终筛选排序..."}, ensure_ascii=False)}\n\n')

    candidates_json = json.dumps(all_found_videos, ensure_ascii=False, indent=2)
    final_prompt = FINAL_SCREENING_PROMPT.format(
        module_title=module_title,
        source_resource_content=source_resource_content[:3000] if source_resource_content else "无详细内容",
        candidates_json=candidates_json
    )

    try:
        final_result = llm.chat_json([{"role": "user", "content": final_prompt}])
        logger.info(f"  [VideoSearchAgent] 最终筛选思考: {final_result.get('thought', '')}")
        final_videos = final_result.get("videos", [])
        logger.info(f"  [VideoSearchAgent] 筛选完成，保留 {len(final_videos)} 个视频")
        return final_videos[:10]
    except Exception as e:
        logger.warning(f"  [VideoSearchAgent] 最终筛选异常: {e}")
        # 如果筛选报错，退化为返回最多 10 个候选
        return all_found_videos[:10]
