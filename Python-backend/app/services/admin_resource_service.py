"""
管理员资源生成与入库服务
- 文本生成：MIMO LLM 流式生成 Markdown 学习内容
- 图片生成：豆包 doubao-seedream 模型生成图片
- 入库：文本分块/图片向量化后存入 Qdrant
"""
import os
import re
import uuid
import json
import asyncio
import logging
import requests
import tempfile
from typing import AsyncGenerator, Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor
from app.core.config import settings
from app.services.embedding import BailianEmbeddingService, SparseEmbeddingService
from app.services.vector_db import QdrantService
from app.services.oss import QiniuOSSService
from app.utils.md_parser import parse_markdown

logger = logging.getLogger("admin_resource")

# 复用入库线程池
_executor = ThreadPoolExecutor(max_workers=5)


class AdminResourceService:
    def __init__(self):
        self.embedding_service = BailianEmbeddingService()
        self.sparse_embedding_service = SparseEmbeddingService()
        self.vector_db = QdrantService()
        self.oss_service = QiniuOSSService()
        # 确保图片临时目录存在
        self._tmp_dir = os.path.join(os.getcwd(), "data", "admin_gen_images")
        os.makedirs(self._tmp_dir, exist_ok=True)

    # ==================== 文本生成 (SSE 流式) ====================

    async def generate_text_stream(
        self, topic: str, custom_prompt: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        SSE 流式生成文本学习内容。
        yield 的每个字符串是增量文本片段。
        """
        from app.agents.llm_factory import MIMOClient, THINKING_DISABLED

        llm = MIMOClient(
            model=MIMOClient.MODEL_PRO,
            temperature=0.7,
            max_tokens=65536,
            thinking=THINKING_DISABLED,
        )

        system_prompt = (
            "你是一位专业的学习内容创作专家。请根据用户给定的主题，生成一篇高质量的学习资料。\n"
            "要求：\n"
            "1. 使用 Markdown 格式，包含标题、小节、要点列表、代码块（如适用）\n"
            "2. 内容准确、结构清晰、适合学习者阅读\n"
            "3. 每个小节配有一句话总结\n"
            "4. 包含关键概念解释和实际示例\n"
            "5. 最后附上参考来源或推荐阅读\n"
            "6. 如果主题适合配图，在文中合适位置用文字描述建议配图的内容（用 > 📷 建议配图：... 的引用块格式）"
        )

        if custom_prompt:
            system_prompt += f"\n\n用户的额外要求：{custom_prompt}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请为以下主题生成学习资料：{topic}"},
        ]

        loop = asyncio.get_running_loop()

        # 在线程池中运行同步的流式 LLM 调用
        def _run_stream():
            for chunk in llm.chat_stream(messages):
                yield chunk

        # 将同步生成器桥接到异步
        # 注意：不能直接用 next(gen) + run_in_executor，因为 StopIteration 无法穿越 Future 边界
        # 改用队列 + 线程的方式
        queue: asyncio.Queue = asyncio.Queue()
        _SENTINEL = object()

        def _producer():
            try:
                for chunk in llm.chat_stream(messages):
                    asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(_SENTINEL), loop)

        _executor.submit(_producer)

        while True:
            item = await queue.get()
            if item is _SENTINEL:
                break
            yield item

    # ==================== 图文一体化生成 (SSE) ====================

    # 匹配 "> 📷 建议配图：xxx" 或 "> 📷 建议配图:xxx"（支持换行）
    _IMAGE_MARKER_RE = re.compile(r'^>\s*📷\s*建议配图[：:]\s*(.+?)(?:\n|$)', re.MULTILINE)

    async def generate_text_with_images_stream(
        self, topic: str, custom_prompt: str = ""
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        图文一体化生成 SSE 流。
        yield 的每个字典是一个 SSE 事件：
        - {"type": "text_chunk", "content": "..."}     文本增量
        - {"type": "text_done", "content": "..."}       文本生成完毕
        - {"type": "image_start", "index": N, "prompt": "..."}  开始生成第 N 张图
        - {"type": "image_done", "index": N, "url": "..."}      第 N 张图生成完毕
        - {"type": "done", "content": "..."}            最终合并的完整内容
        - {"type": "error", "content": "..."}           错误
        """
        try:
            # ========== 阶段1：流式生成文本 ==========
            full_text = ""
            async for chunk in self.generate_text_stream(topic, custom_prompt):
                full_text += chunk
                yield {"type": "text_chunk", "content": chunk}

            yield {"type": "text_done", "content": full_text}

            # ========== 阶段2：提取图片描述 ==========
            image_prompts = self._IMAGE_MARKER_RE.findall(full_text)

            if not image_prompts:
                # 没有配图标记，直接返回文本
                yield {"type": "done", "content": full_text}
                return

            # 限制最多 5 张图，避免生图太慢
            image_prompts = image_prompts[:5]

            # ========== 阶段3：并发生成图片 ==========
            loop = asyncio.get_running_loop()
            image_results: List[Dict[str, str]] = [None] * len(image_prompts)

            async def _gen_one(idx: int, prompt: str):
                yield {"type": "image_start", "index": idx, "prompt": prompt}
                try:
                    result = await loop.run_in_executor(
                        _executor, self._generate_image_sync, prompt
                    )
                    image_results[idx] = result
                    yield {"type": "image_done", "index": idx, "url": result["url"]}
                except Exception as e:
                    logger.error(f"[图文生成] 第 {idx+1} 张图失败: {e}")
                    image_results[idx] = None
                    yield {"type": "image_done", "index": idx, "url": ""}

            # 用 asyncio.gather 并发，但逐个 yield 事件
            # 先创建所有任务
            tasks = []
            for idx, prompt in enumerate(image_prompts):
                tasks.append(_gen_one(idx, prompt))

            # 并发执行所有生成任务，收集事件
            pending = set()
            for gen in tasks:
                pending.add(asyncio.create_task(self._collect_generator(gen)))

            # 等待所有完成
            results = await asyncio.gather(*pending, return_exceptions=True)

            # yield 所有事件（按 index 排序）
            all_events = []
            for r in results:
                if isinstance(r, list):
                    all_events.extend(r)
            all_events.sort(key=lambda e: e.get("index", 0))
            for event in all_events:
                yield event

            # ========== 阶段4：合并文本和图片 ==========
            # 直接用「建议配图：」后面的描述作为图片说明
            final_content = self._merge_text_and_images(full_text, image_prompts, image_results)
            yield {"type": "done", "content": final_content}

        except Exception as e:
            logger.error(f"[图文生成] 失败: {e}", exc_info=True)
            yield {"type": "error", "content": str(e)}

    async def _collect_generator(self, gen) -> list:
        """收集异步生成器的所有值到列表"""
        results = []
        async for item in gen:
            results.append(item)
        return results

    def _merge_text_and_images(
        self, text: str, image_prompts: List[str], image_results: List[Dict[str, str]]
    ) -> str:
        """
        将生成的图片替换回文本中的配图标记位置。
        直接用「建议配图：」后面的描述作为图片说明。
        """
        result = text
        for idx, (prompt, img_data) in enumerate(zip(image_prompts, image_results)):
            # 匹配原始标记行
            marker_pattern = re.compile(
                r'(^>\s*📷\s*建议配图[：:]\s*' + re.escape(prompt) + r'.*?$)',
                re.MULTILINE
            )
            match = marker_pattern.search(result)
            if not match:
                continue

            if img_data and img_data.get("url"):
                # 用 prompt 本身作为图片说明，生成 figure 格式
                caption = prompt.strip()
                replacement = (
                    f'<figure class="rich-image">'
                    f'<img src="{img_data["url"]}" alt="{caption}" />'
                    f'<figcaption>{caption}</figcaption>'
                    f'</figure>'
                )
            else:
                # 图片生成失败，保留原始标记
                continue

            result = result[:match.start()] + replacement + result[match.end():]

        return result

    # ==================== 润色提示词 ====================

    async def polish_prompt(self, prompt: str, mode: str = "text") -> str:
        """
        用 LLM 润色用户的提示词，使其更详细、更有效。
        mode: text(文本生成) / image(图片生成) / rich(图文一体)
        """
        from app.agents.llm_factory import MIMOClient, THINKING_DISABLED

        mode_descriptions = {
            "text": "学习资料文本生成",
            "image": "AI 绘图生成",
            "rich": "图文并茂的学习资料生成",
        }
        mode_desc = mode_descriptions.get(mode, "内容生成")

        system_prompt = (
            f"你是一个提示词优化专家。用户将给你一个简短的描述，用于{mode_desc}。\n"
            "你的任务是将用户的描述润色成一个更详细、更有效的提示词。\n\n"
            "要求：\n"
            "1. 保留用户的原始意图，不要改变主题\n"
            "2. 补充必要的细节、约束和期望\n"
            "3. 使描述更清晰、更具体\n"
            "4. 保持简洁，不要过度冗长\n\n"
        )

        if mode == "image":
            system_prompt += (
                "这是用于 AI 绘图的提示词，请：\n"
                "- 描述画面的具体内容、构图、风格\n"
                "- 加入视觉细节（颜色、光影、视角）\n"
                "- 输出中文描述即可\n"
            )
        elif mode == "text":
            system_prompt += (
                "这是用于生成学习资料的提示词，请：\n"
                "- 明确学习目标和受众\n"
                "- 指定内容深度和范围\n"
                "- 可以加入格式要求\n"
            )
        else:
            system_prompt += (
                "这是用于生成图文并茂学习资料的提示词，请：\n"
                "- 明确学习目标和受众\n"
                "- 指定内容深度和配图风格\n"
                "- 可以加入格式要求\n"
            )

        system_prompt += (
            "\n重要：只输出润色后的提示词本身。"
            "禁止添加任何解释、前缀或说明。"
            "禁止以\"好的\"、\"以下是\"等开头。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        llm = MIMOClient(
            model=MIMOClient.MODEL_STANDARD,  # mimo-v2.5
            temperature=0.5,
            max_tokens=2048,
            thinking=THINKING_DISABLED,
        )

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: llm.chat(messages),
        )

        # 去除可能的引号包裹
        result = result.strip()
        if result.startswith('"') and result.endswith('"'):
            result = result[1:-1]
        if result.startswith('「') and result.endswith('」'):
            result = result[1:-1]

        return result

    # ==================== 智能改写 (SSE 流式) ====================

    async def rewrite_stream(
        self, content: str, requirement: str, topic: str = ""
    ) -> AsyncGenerator[str, None]:
        """
        SSE 流式智能改写。
        接收整篇内容和修改要求，LLM 只修改用户要求的部分，输出完整内容。
        """
        from app.agents.llm_factory import MIMOClient, THINKING_DISABLED

        system_prompt = (
            "你是一个专业的文本编辑工具。用户会给你一篇完整的学习资料和一个修改要求。\n\n"
            "你的任务：\n"
            "1. 只对用户要求修改的部分进行改动\n"
            "2. 用户没有提到的内容必须原样保留，一个字都不能改\n"
            "3. 保持原文的 Markdown 格式、结构和风格\n"
            "4. 输出修改后的完整文本\n\n"
            "禁止：\n"
            "- 禁止添加任何开场白、前缀说明或总结（如\"好的\"、\"以下是\"、\"这是\"）\n"
            "- 禁止对用户未要求修改的内容做任何改动\n"
            "- 禁止添加额外的解释或说明\n\n"
            "直接输出修改后的完整文本。"
        )

        messages = [{"role": "system", "content": system_prompt}]

        user_content = ""
        if topic:
            user_content += f"资源主题：{topic}\n\n"
        user_content += f"修改要求：{requirement}\n\n"
        user_content += f"完整原文：\n{content}"

        messages.append({"role": "user", "content": user_content})

        llm = MIMOClient(
            model=MIMOClient.MODEL_PRO,
            temperature=0.3,  # 低温度，减少额外发挥
            max_tokens=65536,
            thinking=THINKING_DISABLED,
        )

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        _SENTINEL = object()

        def _producer():
            try:
                for chunk in llm.chat_stream(messages):
                    asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(_SENTINEL), loop)

        _executor.submit(_producer)

        while True:
            item = await queue.get()
            if item is _SENTINEL:
                break
            yield item

    # ==================== 图片生成 ====================

    async def generate_image(self, prompt: str) -> Dict[str, str]:
        """
        调用豆包 doubao-seedream 生成图片，上传七牛云，返回 {url, caption}。
        同步阻塞操作，在线程池中执行。
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_executor, self._generate_image_sync, prompt)

    def _generate_image_sync(self, prompt: str) -> Dict[str, str]:
        """同步执行图片生成 + 上传"""
        from volcenginesdkarkruntime import Ark

        client = Ark(
            base_url=settings.ARK_BASE_URL,
            api_key=settings.ARK_API_KEY,
        )

        logger.info(f"[图片生成] 调用豆包 API, prompt={prompt[:80]}...")
        response = client.images.generate(
            model=settings.ARK_IMAGE_MODEL,
            prompt=prompt,
            size="2K",
            output_format="png",
            response_format="url",
            watermark=False,
        )

        image_url = response.data[0].url
        logger.info(f"[图片生成] 豆包返回 URL: {image_url[:80]}...")

        # 下载图片到临时文件
        img_data = requests.get(image_url, timeout=60).content
        tmp_filename = f"{uuid.uuid4()}.png"
        tmp_path = os.path.join(self._tmp_dir, tmp_filename)
        with open(tmp_path, "wb") as f:
            f.write(img_data)

        # 上传到七牛云
        remote_name = f"admin_gen/{tmp_filename}"
        qiniu_url = self.oss_service.upload_file(tmp_path, remote_name)
        logger.info(f"[图片生成] 七牛云上传成功: {qiniu_url}")

        # 清理临时文件
        try:
            os.remove(tmp_path)
        except OSError:
            pass

        return {"url": qiniu_url, "caption": prompt}

    # ==================== 入库 (向量化 + 存 Qdrant) ====================

    async def ingest_text(
        self, title: str, content: str, doc_id: int
    ) -> Dict[str, Any]:
        """
        文本入库：分块 → 向量化 → 存入 Qdrant。
        复用 md_parser 的 split_lines_with_overlap 进行分块。
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _executor, self._ingest_text_sync, title, content, doc_id
        )

    def _ingest_text_sync(
        self, title: str, content: str, doc_id: int
    ) -> Dict[str, Any]:
        """
        同步执行文本分块、向量化、入库。
        与 KB 文档入库流程完全一致：
        1. parse_markdown() 生成小切块 + parent 大切块
        2. 保存 parent JSON 到 data/parents/{doc_id}.json
        3. 逐块向量化，流式同步到 Qdrant
        """
        # 1. 使用与 KB 相同的分块逻辑
        chunks, parent_chunks = parse_markdown(content, doc_id, title)

        if not chunks:
            return {"status": "error", "message": "内容为空，无法入库", "chunk_count": 0}

        # 2. 保存 parent chunks 到本地 JSON（检索时用于加载上下文）
        parents_dir = os.path.join(os.getcwd(), "data", "parents")
        os.makedirs(parents_dir, exist_ok=True)
        parent_json_path = os.path.join(parents_dir, f"{doc_id}.json")
        with open(parent_json_path, "w", encoding="utf-8") as f:
            json.dump(parent_chunks, f, ensure_ascii=False, indent=2)
        logger.info(f"[文本入库] parent chunks 已保存: {parent_json_path}")

        # 3. 逐块向量化入库
        processed_points = []
        success_count = 0
        skipped = 0

        for idx, chunk in enumerate(chunks, 1):
            try:
                if chunk["type"] == "text":
                    if not chunk["content"] or not chunk["content"].strip():
                        skipped += 1
                        continue

                    dense_vector = self.embedding_service.embed_query(chunk["content"])
                    sparse_vector = self.sparse_embedding_service.embed_text(chunk["content"])

                    if not dense_vector:
                        logger.warning(f"[文本入库] 第 {idx} 块稠密向量为空，跳过")
                        skipped += 1
                        continue

                    vector_dict = {"text-dense": dense_vector}
                    if sparse_vector and sparse_vector.get("indices") and len(sparse_vector["indices"]) > 0:
                        vector_dict["text-sparse"] = sparse_vector

                    payload = chunk.copy()
                    processed_points.append({
                        "id": chunk["id"],
                        "vector": vector_dict,
                        "payload": payload,
                    })
                    success_count += 1

                else:
                    # 图片类型的切块（AI 生成的文本一般没有图片，但以防万一）
                    skipped += 1
                    continue

                # 流式同步
                if len(processed_points) >= 20:
                    self.vector_db.upsert_points(processed_points)
                    processed_points = []

            except Exception as e:
                logger.error(f"[文本入库] 第 {idx} 块处理失败: {e}")
                skipped += 1
                continue

        # 处理剩余
        if processed_points:
            self.vector_db.upsert_points(processed_points)

        # 重新写入 parent JSON（与 KB 流程一致）
        with open(parent_json_path, "w", encoding="utf-8") as f:
            json.dump(parent_chunks, f, ensure_ascii=False, indent=2)

        logger.info(f"[文本入库] 完成: doc_id={doc_id}, chunks={success_count}, skipped={skipped}")
        return {
            "status": "success",
            "doc_id": doc_id,
            "chunk_count": success_count,
        }

    async def ingest_image(
        self, image_url: str, caption: str, doc_id: int
    ) -> Dict[str, Any]:
        """
        图片入库：下载图片 → 向量化 → 存入 Qdrant。
        使用融合模式 (image + caption) 生成稠密向量。
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _executor, self._ingest_image_sync, image_url, caption, doc_id
        )

    def _ingest_image_sync(
        self, image_url: str, caption: str, doc_id: int
    ) -> Dict[str, Any]:
        """同步执行图片向量化入库"""
        try:
            # 下载图片到临时文件（embedding 需要本地路径）
            img_data = requests.get(image_url, timeout=60).content
            tmp_path = os.path.join(self._tmp_dir, f"{uuid.uuid4()}.png")
            with open(tmp_path, "wb") as f:
                f.write(img_data)

            # 向量化：融合模式 (image + caption)
            dense_vector = self.embedding_service.embed_image(tmp_path, caption)
            sparse_vector = self.sparse_embedding_service.embed_text(caption)

            # 清理临时文件
            try:
                os.remove(tmp_path)
            except OSError:
                pass

            if not dense_vector:
                return {"status": "error", "message": "图片向量化失败", "chunk_count": 0}

            vector_dict = {"text-dense": dense_vector}
            if sparse_vector and sparse_vector.get("indices") and len(sparse_vector["indices"]) > 0:
                vector_dict["text-sparse"] = sparse_vector

            point_id = str(uuid.uuid4())
            payload = {
                "id": point_id,
                "doc_id": doc_id,
                "doc_title": f"资源库图片",
                "type": "image",
                "content": "",
                "parent_id": str(uuid.uuid4()),
                "image_path": image_url,
                "image_caption": caption,
                "heading": ["资源库", "AI生成图片"],
                "page_num": 0,
            }

            self.vector_db.upsert_points([{
                "id": point_id,
                "vector": vector_dict,
                "payload": payload,
            }])

            logger.info(f"[图片入库] 完成: doc_id={doc_id}, url={image_url[:60]}")
            return {"status": "success", "doc_id": doc_id, "chunk_count": 1}

        except Exception as e:
            logger.error(f"[图片入库] 失败: {e}")
            return {"status": "error", "message": str(e), "chunk_count": 0}

    def delete_vectors(self, doc_id: int):
        """删除指定 doc_id 在 Qdrant 中的所有向量 + parent JSON"""
        self.vector_db.delete_document_chunks(doc_id)

        # 清理 parent JSON 文件（与 KB 流程一致）
        parent_file = os.path.join(os.getcwd(), "data", "parents", f"{doc_id}.json")
        if os.path.exists(parent_file):
            os.remove(parent_file)
            logger.info(f"[资源库] 已删除 parent 文件: {parent_file}")

        logger.info(f"[资源库] 已删除 doc_id={doc_id} 的向量数据")


# 单例
admin_resource_service = AdminResourceService()
