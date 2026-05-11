"""
LLM 工厂 - 为不同智能体提供不同模型配置
所有智能体均不采用思考模式
"""
import requests
import json
from typing import Generator, Optional, Dict, Any
from app.core.config import settings


class MIMOClient:
    """小米 MIMO 模型客户端 (OpenAI 兼容接口)"""

    # 模型配置：编排智能体用 mimo-v2.5，其余用 mimo-v2.5-pro
    MODEL_STANDARD = "mimo-v2.5"       # 编排智能体
    MODEL_PRO = "mimo-v2.5-pro"        # 其余智能体

    def __init__(self, model: str = MODEL_PRO, temperature: float = 0.7, max_tokens: int = 4096):
        self.api_key = settings.MIMO_API_KEY
        self.base_url = settings.MIMO_BASE_URL
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def chat(
        self,
        messages: list,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """同步对话"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": stream,
        }

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        resp = requests.post(url, headers=headers, json=payload, timeout=120)

        if resp.status_code == 200:
            result = resp.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            raise Exception(f"MIMO API 调用失败 ({resp.status_code}): {resp.text}")

    def chat_stream(
        self,
        messages: list,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """流式对话 - 返回增量文本"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": True,
        }

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)

        if resp.status_code != 200:
            raise Exception(f"MIMO API 流式调用失败 ({resp.status_code}): {resp.text}")

        for line in resp.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data = line[6:]
                if data.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue

    def chat_json(
        self,
        messages: list,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """对话并解析 JSON 返回，带容错处理"""
        raw = self.chat(messages, temperature=temperature, max_tokens=max_tokens)
        
        # 尝试提取 JSON
        raw = raw.strip()
        
        # 去掉 markdown 代码块标记
        if raw.startswith("```"):
            lines = raw.split("\n")
            # 去掉第一行（```json 或 ```）和最后一行（```）
            if lines[-1].strip() == "```":
                raw = "\n".join(lines[1:-1])
            else:
                raw = "\n".join(lines[1:])
            raw = raw.strip()
        
        # 尝试多种 JSON 解析策略
        try:
            # 策略1: 直接解析
            return json.loads(raw)
        except json.JSONDecodeError as e:
            # 策略2: 尝试修复常见问题
            try:
                # 移除可能的 BOM 和其他不可见字符
                raw_cleaned = raw.encode('utf-8').decode('utf-8-sig').strip()
                return json.loads(raw_cleaned)
            except json.JSONDecodeError:
                # 策略3: 尝试提取 JSON 对象（查找第一个 { 到最后一个 }）
                try:
                    start = raw.find('{')
                    end = raw.rfind('}')
                    if start != -1 and end != -1 and end > start:
                        json_str = raw[start:end+1]
                        return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
                
                # 策略4: 尝试提取 JSON 数组（查找第一个 [ 到最后一个 ]）
                try:
                    start = raw.find('[')
                    end = raw.rfind(']')
                    if start != -1 and end != -1 and end > start:
                        json_str = raw[start:end+1]
                        return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
                
                # 所有策略都失败，抛出原始错误
                raise Exception(f"JSON 解析失败: {str(e)}\n原始内容前500字符: {raw[:500]}")


def get_controller_llm() -> MIMOClient:
    """主控智能体 - pro 模型，较低温度确保路由准确"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.3, max_tokens=2048)


def get_task_decomposer_llm() -> MIMOClient:
    """任务分解智能体 - pro 模型"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.5, max_tokens=4096)


def get_simple_answer_llm() -> MIMOClient:
    """简答智能体 - pro 模型"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.7, max_tokens=2048)


def get_rag_retriever_llm() -> MIMOClient:
    """RAG 检索智能体 - pro 模型，用于检索词优化"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.3, max_tokens=1024)


def get_content_orchestrator_llm() -> MIMOClient:
    """内容编排智能体 - 标准模型（唯一使用 mimo-v2.5 的智能体）"""
    return MIMOClient(model=MIMOClient.MODEL_STANDARD, temperature=0.5, max_tokens=32678)


def get_reviewer_llm() -> MIMOClient:
    """审查智能体 - pro 模型，低温度确保判断准确"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.2, max_tokens=2048)


def get_resource_generator_llm() -> MIMOClient:
    """多模态资源自主生成智能体 - pro 模型"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.7, max_tokens=16384)


def get_quiz_generator_llm() -> MIMOClient:
    """题目生成智能体 - pro 模型"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.5, max_tokens=4096)


def get_quiz_grader_llm() -> MIMOClient:
    """题目判定智能体 - pro 模型"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.2, max_tokens=2048)


def get_profile_maintainer_llm() -> MIMOClient:
    """画像维护智能体 - pro 模型"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.3, max_tokens=2048)
