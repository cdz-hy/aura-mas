import logging
import dashscope
from http import HTTPStatus
from typing import List, Dict, Any, Generator
from app.core.config import settings
from app.prompts import QWEN_CHAT_SYSTEM_PROMPT

logger = logging.getLogger("services.llm")

class QwenChatService:
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.model = settings.QWEN_CHAT_MODEL

    def generate_response(self, query: str, context_chunks: List[Dict[str, Any]],
                          user_id: int = 0, scene: str = "qwen_chat") -> Generator[str, None, None]:
        """
        结合检索到的上下文，调用 Qwen 模型生成回答（流式输出）。
        支持文本和图片类型的 context_chunk，图片会在 prompt 中以 URL 形式传入，
        指示 LLM 使用 Markdown 格式 ![描述](URL) 在回答中引用图片。
        """
        # 构造增强提示词，区分文本和图片类型
        context_parts = []
        for i, item in enumerate(context_chunks):
            heading_str = " > ".join(item.get("heading", []))
            source_label = f"参考资料 [{i+1}] ({item.get('doc_title', '')} - {heading_str})"

            if item.get("type") == "image":
                image_url = item.get("image_path", "")
                caption = item.get("image_caption", "")
                content = item.get("content", "")
                part = (
                    f"{source_label}:\n"
                    f"[图片资料] URL: {image_url}\n"
                    f"图片 AI 描述: {caption}\n"
                    f"上下文内容: {content}"
                )
            else:
                part = f"{source_label}:\n{item.get('content', '')}"

            context_parts.append(part)

        context_str = "\n\n".join(context_parts)

        system_prompt = QWEN_CHAT_SYSTEM_PROMPT

        user_content = f"参考资料：\n{context_str}\n\n用户问题：\n{query}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        responses = dashscope.Generation.call(
            model=self.model,
            messages=messages,
            api_key=self.api_key,
            result_format='message',
            stream=True
        )

        last_usage = None
        for response in responses:
            if response.status_code == HTTPStatus.OK:
                usage = getattr(response, "usage", None)
                if usage:
                    last_usage = {
                        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
                        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
                    }
                yield response.output.choices[0].message.content
            else:
                logger.error("Dashscope API 错误: status=%s message=%s model=%s", response.status_code, response.message, self.model)
                yield f"AI 生成失败: {response.message}"

        if last_usage:
            from app.utils.token_recorder import record
            record(
                user_id=user_id,
                scene=scene,
                model_name=self.model,
                input_tokens=last_usage["input_tokens"],
                output_tokens=last_usage["output_tokens"],
            )
