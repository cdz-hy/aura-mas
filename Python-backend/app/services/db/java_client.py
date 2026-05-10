"""
Java 后端 HTTP 客户端 - 用于多智能体系统与 Java 后端的数据交互
所有数据库操作通过 Java 后端的内部 API 完成
"""
import json
import base64
import logging
import requests
from typing import Optional, List, Dict, Any
from app.core.config import settings

logger = logging.getLogger("java_client")


class JavaBackendClient:
    """Java 后端内部 API 客户端"""

    def __init__(self):
        self.base_url = settings.JAVA_BACKEND_URL.rstrip("/")
        self.timeout = 30

    def validate_ticket(self, ticket: str) -> Dict[str, Any]:
        """
        验证 Java 后端签发的短期 Ticket（JWT），返回解码后的 payload。
        Ticket JWT 结构: header.payload.signature，payload 中包含 userId, loginName, role, type=ticket

        采用 payload 解码方式：ticket 是短期 JWT（5 分钟过期），
        由前端从 Java 后端获取后直传 Python，安全风险极低，直接解码 payload 即可。
        """
        try:
            parts = ticket.split(".")
            if len(parts) != 3:
                raise Exception("Invalid JWT format")

            # 解码 payload（JWT 使用 URL-safe Base64 无 padding）
            payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_bytes)

            # 检查 ticket 类型
            if payload.get("type") != "ticket":
                raise Exception("Not a ticket token")

            # 检查是否过期
            exp = payload.get("exp")
            if exp:
                import time
                if time.time() > exp:
                    raise Exception("Ticket expired")

            user_id = payload.get("userId") or payload.get("sub")
            if not user_id:
                raise Exception("No userId in ticket")

            return {
                "user_id": int(user_id),
                "login_name": payload.get("loginName", ""),
                "role": payload.get("role", "student"),
            }
        except Exception as e:
            raise Exception(f"Ticket 验证失败: {str(e)}")

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.timeout)
        try:
            resp = requests.request(method, url, **kwargs)
            if resp.status_code == 200:
                result = resp.json()
                code = result.get("code", 200)
                if code == 200 or code == 0:
                    return result.get("data", result)
                else:
                    raise Exception(f"Java 后端返回错误: {result.get('msg', '未知错误')}")
            else:
                raise Exception(f"Java 后端请求失败 ({resp.status_code}): {resp.text}")
        except requests.exceptions.ConnectionError:
            raise Exception(f"无法连接 Java 后端: {url}")
        except requests.exceptions.Timeout:
            raise Exception(f"Java 后端请求超时: {url}")

    # ==================== 对话记录 ====================

    def create_dialogue(
        self,
        user_id: int,
        session_id: str,
        conversation_text: str,
        dialogue_type: str,
        plan_id: Optional[int] = None,
        intent_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """创建对话记录"""
        body = {
            "userId": user_id,
            "sessionId": session_id,
            "conversationText": conversation_text,
            "dialogueType": dialogue_type,
        }
        if plan_id is not None:
            body["planId"] = plan_id
        if intent_type is not None:
            body["intentType"] = intent_type
        return self._request("POST", "/api/internal/dialogue", json=body)

    def update_dialogue_resource_id(self, dialogue_id: int, resource_id: int):
        """更新对话记录的资源ID"""
        return self._request("PUT", f"/api/internal/dialogue/{dialogue_id}/resource", params={"resourceId": resource_id})

    def get_dialogue_history(
        self,
        user_id: int,
        plan_id: Optional[int] = None,
        session_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """获取对话历史"""
        params = {"userId": user_id, "limit": limit}
        if plan_id:
            params["planId"] = plan_id
        if session_id:
            params["sessionId"] = session_id
        return self._request("GET", "/api/internal/dialogue/history", params=params)

    # ==================== 学习计划 ====================

    def create_plan(
        self,
        user_id: int,
        title: str,
        learning_goal: Any,
        plan_config: Any = None,
        status: int = 0,
    ) -> Dict[str, Any]:
        """创建学习计划"""
        return self._request("POST", "/api/plan/internal/create", json={
            "userId": user_id,
            "title": title,
            "learningGoal": learning_goal if isinstance(learning_goal, str) else json.dumps(learning_goal, ensure_ascii=False),
            "planConfig": plan_config if isinstance(plan_config, str) else (json.dumps(plan_config, ensure_ascii=False) if plan_config else None),
            "status": status,
        })

    def get_plan(self, plan_id: int) -> Dict[str, Any]:
        """获取学习计划"""
        return self._request("GET", f"/api/plan/internal/{plan_id}")

    def update_plan_status(self, plan_id: int, status: int):
        """更新计划状态"""
        self._request("PUT", f"/api/plan/{plan_id}/status", params={"status": status})

    # ==================== 学习资源 ====================

    def create_resource(
        self,
        plan_id: int,
        module_type: str,
        module_data: Any,
        module_order: int = 0,
        parent_id: Optional[int] = None,
        status: int = 2,
        generated_by_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """创建单个学习资源模块"""
        resource = {
            "planId": plan_id,
            "moduleType": module_type,
            "moduleData": module_data if isinstance(module_data, str) else json.dumps(module_data, ensure_ascii=False),
            "moduleOrder": module_order,
            "status": status,
        }
        if parent_id is not None:
            resource["parentId"] = parent_id
        if generated_by_agent:
            resource["generatedByAgent"] = generated_by_agent
        return self._request("POST", "/api/resource/internal", json=resource)

    def create_resources_bulk(
        self,
        resources: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """批量创建学习资源"""
        return self._request("POST", "/api/resource/internal/bulk", json=resources)

    def get_plan_resources(self, plan_id: int) -> List[Dict[str, Any]]:
        """获取计划的所有资源"""
        return self._request("GET", f"/api/resource/internal/plan/{plan_id}")

    def update_resource_content(self, resource_id: int, module_data: str, status: Optional[int] = None):
        """更新资源内容"""
        body = {"moduleData": module_data}
        if status is not None:
            body["status"] = status
        self._request("PUT", f"/api/resource/internal/{resource_id}/content", json=body)

    def update_resource_status(self, resource_id: int, status: int):
        """更新资源状态"""
        self._request("PUT", f"/api/resource/internal/{resource_id}/status", params={"status": status})

    # ==================== 答题记录 ====================

    def create_quiz_record(
        self,
        resource_id: int,
        user_id: int,
        plan_id: int,
        question_type: str,
        correct_answer: str,
        user_answer: str,
        is_correct: int,
        difficulty: int = 3,
    ) -> Dict[str, Any]:
        """创建答题记录"""
        return self._request("POST", "/api/quiz/internal/create", json={
            "resourceId": resource_id,
            "userId": user_id,
            "planId": plan_id,
            "questionType": question_type,
            "correctAnswer": correct_answer,
            "userAnswer": user_answer,
            "isCorrect": is_correct,
            "difficulty": difficulty,
        })

    def get_user_quiz_stats(self, user_id: int, plan_id: int) -> Dict[str, Any]:
        """获取用户答题统计"""
        return self._request("GET", f"/api/quiz/internal/stats/{plan_id}", params={"userId": user_id})

    # ==================== 用户画像 ====================

    def get_user_profile(self, user_id: int) -> Dict[str, Any]:
        """获取用户当前画像"""
        return self._request("GET", f"/api/internal/profile/current", params={"userId": user_id})

    def get_resource_by_id(self, resource_id: int) -> Dict[str, Any]:
        """获取单个学习资源"""
        return self._request("GET", f"/api/resource/internal/{resource_id}")

    def update_user_profile(
        self,
        user_id: int,
        learning_behavior: Dict[str, Any],
        update_reason: str,
    ) -> Dict[str, Any]:
        """更新用户画像"""
        return self._request("PUT", "/api/internal/profile", json={
            "userId": user_id,
            "learningBehavior": json.dumps(learning_behavior, ensure_ascii=False),
            "updateReason": update_reason,
        })

    def create_user_profile(
        self,
        user_id: int,
        learning_behavior: Dict[str, Any],
        update_reason: str = "初始创建",
    ) -> Dict[str, Any]:
        """创建用户画像（当用户无画像时使用）"""
        return self._request("POST", "/api/internal/profile", json={
            "userId": user_id,
            "learningBehavior": json.dumps(learning_behavior, ensure_ascii=False),
            "updateReason": update_reason,
        })

    def save_user_profile(
        self,
        user_id: int,
        learning_behavior: Dict[str, Any],
        update_reason: str,
    ):
        """保存用户画像（自动判断创建或更新）"""
        try:
            self.update_user_profile(user_id, learning_behavior, update_reason)
        except Exception:
            try:
                self.create_user_profile(user_id, learning_behavior, update_reason)
            except Exception as e:
                logger.warning(f"保存用户画像失败: {e}")

    # ==================== 资源生成任务 ====================

    def create_generation_task(
        self,
        plan_id: int,
        resource_id: int,
        agent_chain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """创建资源生成任务"""
        body = {
            "planId": plan_id,
            "resourceId": resource_id,
        }
        if agent_chain:
            body["agentChain"] = agent_chain
        return self._request("POST", "/api/task/internal/create", json=body)

    def update_generation_task(
        self,
        task_id: int,
        task_status: int,
    ) -> Dict[str, Any]:
        """更新资源生成任务状态"""
        return self._request("PUT", f"/api/task/internal/{task_id}", json={
            "taskStatus": task_status,
        })

    # ==================== Token 消耗 ====================

    def record_token_usage(
        self,
        user_id: int,
        scene: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        task_id: Optional[int] = None,
    ):
        """记录 Token 消耗"""
        body = {
            "userId": user_id,
            "scene": scene,
            "modelName": model_name,
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
        }
        if task_id is not None:
            body["taskId"] = task_id
        self._request("POST", "/api/token/internal/record", json=body)


# 全局单例
java_client = JavaBackendClient()
