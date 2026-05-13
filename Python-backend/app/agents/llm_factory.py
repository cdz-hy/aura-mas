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

    # 各模型的上下文窗口上限（max_completion_tokens 上限）
    CONTEXT_WINDOWS = {
        "mimo-v2.5": 131072,
        "mimo-v2.5-pro": 131072,
    }

    # 为输出预留的默认比例（占上下文窗口的 25%），避免输入大时溢出
    OUTPUT_RESERVE_RATIO = 0.25
    
    # 为特殊标记、系统提示词等预留的安全边界
    SAFETY_MARGIN = 1024

    def __init__(self, model: str = MODEL_PRO, temperature: float = 0.7, max_tokens: int = 4096,
                 thinking: Optional[Dict[str, str]] = None):
        self.api_key = settings.MIMO_API_KEY
        self.base_url = settings.MIMO_BASE_URL
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        # 思维链配置：None 表示使用模型默认值（mimo-v2.5-pro 默认 enabled）
        self.thinking = thinking

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """粗略估算 token 数：中文约 1.5 token/字，英文约 0.25 token/字符"""
        cn_chars = sum(1 for c in text if '一' <= c <= '鿿')
        other_chars = len(text) - cn_chars
        return int(cn_chars * 1.5 + other_chars * 0.25)

    def _clamp_max_tokens(self, messages: list, requested_max: int) -> int:
        """确保 input_tokens + max_tokens 不超过模型上下文窗口"""
        ctx_limit = self.CONTEXT_WINDOWS.get(self.model, 32768)
        input_tokens = sum(self._estimate_tokens(m.get("content", "")) for m in messages)
        
        # 预留安全边界给特殊标记、系统提示词等开销
        available = ctx_limit - input_tokens - self.SAFETY_MARGIN
        
        if available < 512:
            raise Exception(
                f"输入过长（约 {input_tokens} tokens），模型 {self.model} 上下文上限 {ctx_limit}，"
                f"已无足够空间生成输出（可用空间 < 512 tokens）"
            )
        
        # 限制 max_tokens 不超过可用空间，且不超过上下文窗口的 60%（避免过度占用）
        max_allowed = min(available, int(ctx_limit * 0.6))
        clamped = min(requested_max, max_allowed)
        
        if clamped < requested_max:
            import logging
            logging.getLogger("llm_factory").warning(
                f"max_tokens 从 {requested_max} 自动降至 {clamped}（输入约 {input_tokens} tokens，"
                f"模型上限 {ctx_limit}，可用空间 {available}）"
            )
        return clamped

    def _build_payload(self, messages: list, stream: bool = False,
                       temperature: Optional[float] = None,
                       max_tokens: Optional[int] = None,
                       response_format: Optional[Dict[str, str]] = None) -> dict:
        """构造 API 请求体"""
        requested = max_tokens or self.max_tokens
        safe_max_tokens = self._clamp_max_tokens(messages, requested)

        payload = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": safe_max_tokens,
            "stream": stream,
        }

        # 思维链：启用时 API 强制 temperature=1.0，无需手动设置
        thinking = self.thinking
        if thinking:
            payload["thinking"] = thinking
            # 思维链模式下 temperature 由 API 控制，不发送
        else:
            payload["temperature"] = temperature or self.temperature

        if response_format:
            payload["response_format"] = response_format

        return payload, safe_max_tokens

    def chat(
        self,
        messages: list,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """同步对话"""
        payload, safe_max_tokens = self._build_payload(
            messages, stream=stream, temperature=temperature,
            max_tokens=max_tokens, response_format=response_format,
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
        except requests.exceptions.Timeout:
            raise Exception("MIMO API 请求超时（120秒），可能是网络问题或服务繁忙")
        except requests.exceptions.RequestException as e:
            raise Exception(f"MIMO API 网络请求失败: {str(e)[:200]}")

        if resp.status_code == 200:
            try:
                result = resp.json()
            except json.JSONDecodeError:
                raise Exception(f"MIMO API 返回非 JSON 格式: {resp.text[:300]}")
            
            choices = result.get("choices", [])
            if not choices:
                raise Exception(f"MIMO API 返回空 choices: {str(result)[:300]}")
            
            content = choices[0].get("message", {}).get("content")
            finish_reason = choices[0].get("finish_reason", "")

            if content is None or content.strip() == "":
                # 记录完整响应以便排查
                import logging
                logger = logging.getLogger("llm_factory")
                logger.warning(
                    f"MIMO API 返回空内容 (finish_reason={finish_reason}, "
                    f"model={self.model}, max_completion_tokens={safe_max_tokens}): "
                    f"{str(choices[0])[:500]}"
                )
                if finish_reason == "content_filter":
                    raise Exception("MIMO API 触发内容安全过滤，请检查输入内容是否包含敏感词")
                elif finish_reason == "length":
                    raise Exception(f"MIMO API 输出被截断（max_completion_tokens={safe_max_tokens} 不足）")
                elif content is None:
                    raise Exception(f"MIMO API 返回 content 为 null (finish_reason: {finish_reason})")

            return (content or "").strip()
        elif resp.status_code == 400:
            # 解析 400 错误的具体原因
            try:
                error_data = resp.json()
                error_msg = error_data.get("error", {}).get("message", resp.text)
            except:
                error_msg = resp.text
            raise Exception(f"MIMO API 请求参数错误 (400): {error_msg[:300]}")
        elif resp.status_code == 429:
            raise Exception("MIMO API 请求频率超限 (429)，请稍后重试或检查配额")
        elif resp.status_code == 500:
            raise Exception(f"MIMO API 服务器错误 (500): {resp.text[:300]}")
        else:
            raise Exception(f"MIMO API 调用失败 ({resp.status_code}): {resp.text[:300]}")

    def chat_stream(
        self,
        messages: list,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Generator[str, None, None]:
        """流式对话 - 返回增量文本（含思维链 reasoning_content）"""
        payload, _ = self._build_payload(
            messages, stream=True, temperature=temperature, max_tokens=max_tokens,
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
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
                    # 思维链内容（reasoning_content）不对外输出，仅调试时记录
                    reasoning = delta.get("reasoning_content", "")
                    if reasoning:
                        import logging
                        logging.getLogger("llm_factory").debug(f"[思维链] {reasoning[:100]}")
                    # 只输出正式内容
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
        """对话并解析 JSON 返回，使用 response_format 强制 JSON 输出"""
        logger = __import__('logging').getLogger("llm_factory")
        json_format = {"type": "json_object"}

        try:
            raw = self.chat(messages, temperature=temperature, max_tokens=max_tokens,
                            response_format=json_format)
        except Exception as e:
            logger.error(f"LLM API 调用失败: {str(e)[:300]}")
            raise Exception(f"LLM API 调用失败: {str(e)[:200]}")

        # 空内容重试
        if not raw or not raw.strip():
            logger.warning(f"LLM 返回空内容，重试... (模型: {self.model})")
            retry_messages = list(messages) + [
                {"role": "user", "content": "你上次的回复为空。请重新回答，严格只输出合法的 JSON。"}
            ]
            try:
                raw = self.chat(retry_messages, temperature=0.0, max_tokens=max_tokens,
                                response_format=json_format)
            except Exception as e:
                raise Exception(f"LLM 重试调用失败: {str(e)[:200]}")
            if not raw or not raw.strip():
                raise Exception("LLM 连续返回空内容，可能是模型服务异常或触发内容过滤")

        result = self._parse_json(raw)
        if result is not None:
            return result

        # response_format=json_object 仍解析失败（极少发生），重试一次
        logger.warning(f"JSON 解析失败（尽管使用了 response_format），重试... 原始内容前200字符: {raw[:200]}")
        retry_messages = list(messages) + [
            {"role": "user", "content": "你上次的回复不是合法的 JSON。请严格只输出合法的 JSON。"}
        ]
        raw_retry = self.chat(retry_messages, temperature=0.0, max_tokens=max_tokens,
                              response_format=json_format)
        result = self._parse_json(raw_retry)
        if result is not None:
            return result

        logger.error(f"JSON 解析失败（重试后仍失败）模型: {self.model}, 原始: {raw[:500]}")
        raise Exception(f"JSON 解析失败（重试后仍失败）\n原始内容前500字符: {raw[:500]}")

    def _parse_json(self, raw: str) -> Optional[Dict[str, Any]]:
        """解析 JSON，返回 dict 或 None（5种策略依次尝试）"""
        import re
        raw = raw.strip()

        # 去掉 markdown 代码块标记
        if raw.startswith("```"):
            lines = raw.split("\n")
            if lines[-1].strip() == "```":
                raw = "\n".join(lines[1:-1])
            else:
                raw = "\n".join(lines[1:])
            raw = raw.strip()

        # 策略1: 直接解析
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # 策略2: 移除 BOM
        try:
            return json.loads(raw.encode('utf-8').decode('utf-8-sig').strip())
        except json.JSONDecodeError:
            pass

        # 策略3: 提取 JSON 对象
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1 and end > start:
            extracted = raw[start:end + 1]
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                # 策略3b: 修复 LLM 常见的 JSON 语法错误
                fixed = self._fix_common_json_errors(extracted)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass

        # 策略4: 提取 JSON 数组
        start = raw.find('[')
        end = raw.rfind(']')
        if start != -1 and end != -1 and end > start:
            extracted = raw[start:end + 1]
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                fixed = self._fix_common_json_errors(extracted)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass

        return None

    @staticmethod
    def _fix_common_json_errors(s: str) -> str:
        """修复 LLM 输出 JSON 中的常见语法错误：尾部逗号、字符串内未转义双引号"""
        import re
        # 1. 移除尾部逗号: {"a":1,} -> {"a":1}
        s = re.sub(r',\s*([\]}])', r'\1', s)
        # 2. 修复字符串内部的未转义双引号
        #    逐字符扫描，遇到字符串内的裸 " 就转义为 \"
        result = []
        in_string = False
        i = 0
        while i < len(s):
            ch = s[i]
            if ch == '\\' and in_string:
                # 转义序列，原样保留两位
                result.append(s[i:i+2])
                i += 2
                continue
            if ch == '"':
                if not in_string:
                    in_string = True
                    result.append(ch)
                else:
                    # 判断这个 " 是字符串结束还是内部裸引号
                    # 看下一个非空白字符：如果是 , : ] } 或到达结尾，则是结束引号
                    rest = s[i+1:].lstrip()
                    if not rest or rest[0] in ',:]}':
                        in_string = False
                        result.append(ch)
                    else:
                        # 内部裸引号，转义它
                        result.append('\\"')
                i += 1
                continue
            result.append(ch)
            i += 1
        return ''.join(result)


THINKING_DISABLED = {"type": "disabled"}
THINKING_ENABLED = {"type": "enabled"}


def get_controller_llm() -> MIMOClient:
    """主控智能体 - pro 模型，关闭思维链 + 低温度，确保路由快速准确"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.3, max_tokens=1536,
                      thinking=THINKING_DISABLED)


def get_task_decomposer_llm() -> MIMOClient:
    """任务分解智能体 - pro 模型，启用思维链"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.5, max_tokens=3072,
                      thinking=THINKING_ENABLED)


def get_simple_answer_llm() -> MIMOClient:
    """简答智能体 - pro 模型，关闭思维链，快速响应"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.7, max_tokens=2048,
                      thinking=THINKING_DISABLED)


def get_rag_retriever_llm() -> MIMOClient:
    """RAG 检索智能体 - pro 模型，关闭思维链，只需生成检索词"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.3, max_tokens=1536,
                      thinking=THINKING_DISABLED)


def get_content_orchestrator_llm() -> MIMOClient:
    """内容编排智能体 - 标准模型（mimo-v2.5，131K 上下文），启用思维链"""
    return MIMOClient(model=MIMOClient.MODEL_STANDARD, temperature=0.5, max_tokens=16384,
                      thinking=THINKING_ENABLED)


def get_reviewer_llm() -> MIMOClient:
    """审查智能体 - pro 模型，关闭思维链，只需判断和评分"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.2, max_tokens=3072,
                      thinking=THINKING_DISABLED)


def get_resource_generator_llm() -> MIMOClient:
    """多模态资源自主生成智能体 - pro 模型，启用思维链"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.7, max_tokens=6144,
                      thinking=THINKING_ENABLED)


def get_quiz_generator_llm() -> MIMOClient:
    """题目生成智能体 - pro 模型，启用思维链"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.5, max_tokens=3072,
                      thinking=THINKING_ENABLED)


def get_quiz_grader_llm() -> MIMOClient:
    """题目判定智能体 - pro 模型，关闭思维链"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.2, max_tokens=1536,
                      thinking=THINKING_DISABLED)


def get_profile_maintainer_llm() -> MIMOClient:
    """画像维护智能体 - pro 模型，关闭思维链"""
    return MIMOClient(model=MIMOClient.MODEL_PRO, temperature=0.3, max_tokens=2048,
                      thinking=THINKING_DISABLED)
