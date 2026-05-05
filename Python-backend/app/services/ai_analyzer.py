import dashscope
from http import HTTPStatus
from app.core.config import settings
import os

class MultiModalAnalyzer:
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.model = settings.QWEN_VL_CHAT_MODEL

    def analyze_image(self, image_path: str, context: str) -> str:
        """
        调用 Qwen-VL 模型对图片进行深度分析，结合上下文生成高质量 Caption
        """
        if not os.path.exists(image_path):
            return "图片文件不存在"

        # 构造提示词
        prompt = f"""
        请根据提供的图片以及其在文档中的上下文内容，为这张图片生成一个专业且详细的描述（Caption）。
        这个描述将用于后续的搜索索引，请确保包含图片中的核心对象、动作、文字信息以及与上下文的关联。
        
        文档上下文：
        {context}
        
        请直接输出生成的描述，不要包含任何多余的解释。
        """

        messages = [
            {
                "role": "user",
                "content": [
                    {"image": f"file://{os.path.abspath(image_path)}"},
                    {"text": prompt}
                ]
            }
        ]

        try:
            response = dashscope.MultiModalConversation.call(
                model=self.model,
                messages=messages,
                api_key=self.api_key
            )

            if response.status_code == HTTPStatus.OK:
                return response.output.choices[0].message.content[0]["text"].strip()
            else:
                print(f"AI 分析图片失败: {response.code} - {response.message}")
                return ""
        except Exception as e:
            print(f"调用 AI 分析服务时发生异常: {e}")
            return ""
