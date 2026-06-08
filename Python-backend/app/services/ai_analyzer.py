import requests
import base64
import os
from app.core.config import settings

class MultiModalAnalyzer:
    def __init__(self):
        self.api_key = settings.MIMO_API_KEY
        self.base_url = settings.MIMO_BASE_URL
        self.model = settings.MIMO_MODEL_NAME

    def _encode_image(self, image_path: str) -> str:
        """将本地图片转换为 Base64 编码"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def analyze_image(self, image_path: str, context: str) -> str:
        """
        调用小米 MIMO-v2.5 模型 (OpenAI 兼容接口) 对图片进行深度分析
        """
        if not os.path.exists(image_path):
            return "图片文件不存在"

        if not self.api_key:
            print("错误: 未配置 MIMO_API_KEY")
            return ""

        # 构造提示词
        prompt = f"""
        请根据提供的图片以及其在文档中的上下文内容，为这张图片生成一个专业且详细的描述（Caption）。
        这个描述将用于后续的搜索索引，请确保包含图片中的核心对象、动作、文字信息以及与上下文的关联。
        
        文档上下文：
        {context}
        
        请直接输出生成的描述，不要包含任何多余的解释。
        """

        base64_image = self._encode_image(image_path)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 500
        }

        try:
            # 拼接完整的聊天补全接口地址
            url = f"{self.base_url.rstrip('/')}/chat/completions"
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"MIMO 分析图片失败: {response.status_code} - {response.text}")
                return ""
        except Exception as e:
            print(f"调用 MIMO 分析服务时发生异常: {e}")
            return ""
