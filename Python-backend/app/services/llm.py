import dashscope
from http import HTTPStatus
from typing import List, Dict, Any, Generator
from app.core.config import settings

class QwenChatService:
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.model = "qwen-plus"

    def generate_response(self, query: str, context_chunks: List[Dict[str, Any]]) -> Generator[str, None, None]:
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

        system_prompt = (
            "你是一个专业的 AI 助手。请根据提供的参考资料回答用户的问题。\n"
            "规则：\n"
            "1. 如果资料中没有相关信息，请诚实告知。\n"
            "2. 回答中尽量引用参考资料编号，保持专业和客观。\n"
            "3. 如果参考资料包含图片 URL，请在回答的合适位置使用 Markdown 格式 ![图片描述](图片URL) 嵌入该图片，不要只描述图片而不展示。\n"
            "4. 严禁在回答中使用任何 emoji 表情符号。"
        )

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

        for response in responses:
            if response.status_code == HTTPStatus.OK:
                yield response.output.choices[0].message.content
            else:
                yield f"AI 生成失败: {response.message}"
