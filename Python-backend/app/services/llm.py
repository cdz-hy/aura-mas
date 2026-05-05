import dashscope
from http import HTTPStatus
from typing import List, Dict, Any, Generator
from app.core.config import settings

class QwenChatService:
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.model = "qwen-plus" # 使用 qwen-plus 进行对话生成

    def generate_response(self, query: str, context_chunks: List[Dict[str, Any]]) -> Generator[str, None, None]:
        """
        结合检索到的上下文，调用 Qwen 模型生成回答（流式输出）
        """
        # 构造增强提示词
        context_str = "\n\n".join([
            f"资料来源 [{i+1}] ({item['doc_title']} - {' > '.join(item['heading'])}):\n{item['content']}"
            for i, item in enumerate(context_chunks)
        ])

        system_prompt = """你是一个专业的 AI 助手。请根据提供的“参考资料”来回答用户的问题。
        如果资料中没有相关信息，请诚实告知。
        请在回答中尽量引用参考资料，并保持回答的专业和客观。
        """

        user_content = f"""参考资料：
        {context_str}
        
        用户问题：
        {query}
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        responses = dashscope.Generation.call(
            model=self.model,
            messages=messages,
            api_key=self.api_key,
            result_format='message',
            stream=True # 开启流式输出
        )

        for response in responses:
            if response.status_code == HTTPStatus.OK:
                yield response.output.choices[0].message.content
            else:
                yield f"AI 生成失败: {response.message}"
