"""
LangGraph 多智能体系统 - 全局状态定义
所有智能体共享此状态结构，通过 LangGraph 的 StateGraph 传递
"""
from typing import TypedDict, List, Optional, Dict, Any, Literal, Annotated
import operator
from pydantic import BaseModel, Field


# ==================== 智能体节点名称常量 ====================
NODE_CONTROLLER = "controller"
NODE_TASK_DECOMPOSER = "task_decomposer"
NODE_SIMPLE_ANSWER = "simple_answer"
NODE_RAG_RETRIEVER = "rag_retriever"
NODE_CONTENT_ORCHESTRATOR = "content_orchestrator"
NODE_REVIEWER = "reviewer"
NODE_REVIEW_ORCHESTRATE = "review_orchestrate"
NODE_REVIEW_ONLY = "review_only"
NODE_RESOURCE_GENERATOR = "resource_generator"
NODE_QUIZ_GENERATOR = "quiz_generator"
NODE_QUIZ_GRADER = "quiz_grader"
NODE_RESOURCE_TYPE_GENERATOR = "resource_type_generator"
NODE_ANIMATION_SKILL_GENERATOR = "animation_skill_generator"
NODE_PROFILE_MAINTAINER = "profile_maintainer"
NODE_HUMAN_CONFIRM = "human_confirm"
NODE_WAIT_USER_REPLY = "wait_user_reply"

# 意图类型
INTENT_GENERATE_RESOURCE = "generate_resource"
INTENT_SIMPLE_QA = "simple_qa"
INTENT_GENERATE_QUIZ = "generate_quiz"
INTENT_GRADE_QUIZ = "grade_quiz"
INTENT_AMBIGUOUS = "ambiguous"
INTENT_FOLLOW_UP = "follow_up"
INTENT_GENERATE_ANIMATION = "generate_animation"
INTENT_GENERATE_TYPE_RESOURCE = "generate_type_resource"
INTENT_CLARIFY = "clarify"
INTENT_CANCEL = "cancel"  # 用户取消/退出生成流程
def reduce_current_step(left: str, right: str) -> str:
    """合并并行节点的状态步骤描述，避免并发冲突"""
    if not left:
        return right or ""
    if not right:
        return left or ""
    # 按 | 分割去重合并
    left_parts = [p.strip() for p in left.split(" | ") if p.strip()]
    right_parts = [p.strip() for p in right.split(" | ") if p.strip()]
    merged = left_parts + [r for r in right_parts if r not in left_parts]
    return " | ".join(merged)

def reduce_error(left: Optional[str], right: Optional[str]) -> Optional[str]:
    """合并并行节点的错误信息，避免并发冲突"""
    if not left:
        return right
    if not right:
        return left
    left_parts = [p.strip() for p in left.split(" ; ") if p.strip()]
    right_parts = [p.strip() for p in right.split(" ; ") if p.strip()]
    merged = left_parts + [r for r in right_parts if r not in left_parts]
    return " ; ".join(merged)


class AgentState(TypedDict, total=False):
    """LangGraph 全局状态 - 所有智能体共享的数据结构"""

    # ==================== 请求基础信息 ====================
    user_id: int
    plan_id: Optional[int]
    task_id: Optional[int]
    session_id: str
    user_message: str  # 当前用户输入
    current_module_id: Optional[int]  # 前端传入的当前正在学习的模块ID
    current_module_title: Optional[str]  # 前端传入的模块标题

    # ==================== 对话上下文 ====================
    chat_history: List[Dict[str, str]]  # [{"role": "user"/"assistant", "content": "..."}]
    accumulated_context: str  # 累积的上下文摘要

    # ==================== 意图与路由 ====================
    intent: str  # 当前识别的意图
    next_node: str  # 下一个要执行的节点
    needs_human_confirm: bool  # 是否需要用户确认
    human_feedback: Optional[str]  # 用户反馈内容
    resource_type: Optional[str]  # 生成类型资源时的具体类型(podcast, mindmap等)

    # ==================== 用户画像 ====================
    user_profile: Dict[str, Any]  # 用户画像数据
    profile_update_needed: bool  # 是否需要更新画像

    # ==================== 任务分解 ====================
    learning_goal: str  # 学习目标
    _checkpoint_learning_goal: str  # 上一轮 checkpointer 中的学习目标（供 controller 意图驱动判定）
    task_breakdown: Optional[Dict[str, Any]]  # 任务分解结果
    task_breakdown_confirmed: bool  # 用户是否已确认分解

    # ==================== RAG 检索 ====================
    search_queries: List[str]  # 优化后的检索词列表
    rag_results: List[Dict[str, Any]]  # RAG 检索结果
    rag_context_chunks: List[Dict[str, Any]]  # 去重后的上下文块
    rag_sufficient: bool  # RAG 检索结果是否充足
    rag_poor_module_ids: List[int]  # RAG 检索结果不足的模块 ID 列表（需自主生成）
    retrieval_config: Dict[str, Any]  # 检索配置（召回数、精排数等）

    # ==================== 审查 ====================
    review_passed: bool  # 审查是否通过
    review_feedback: str  # 审查反馈
    review_suggestions: List[str]  # 优化建议
    failed_modules: List[Dict[str, Any]]  # 未通过审查的模块列表
    passed_modules: List[int]  # 通过审查的模块编号列表
    module_review_results: List[Dict[str, Any]]  # 所有模块的详细审查结果
    retry_module_ids: List[int]  # 需要重新生成的模块编号列表
    retry_mode: bool  # 是否为重试模式
    target_module_ids: List[int]  # 重试模式下的目标模块编号列表
    retry_count: int  # 当前重试次数
    max_retries: int  # 最大重试次数（默认3次）

    # ==================== 内容编排 ====================
    orchestrated_content: Optional[Dict[str, Any]]  # 编排后的模块化内容
    module_list: List[Dict[str, Any]]  # 生成的学习资源模块列表
    use_parallel_orchestration: bool  # 是否使用并行编排模式（默认 True）
    placeholder_resource_map: Dict[int, Dict[str, Any]]  # module_order -> {id, type, title} 占位资源映射

    # ==================== 自主生成 ====================
    generated_content: Optional[Dict[str, Any]]  # 自主生成的内容
    source_resource_content: str  # 源资源全文（用于类型资源生成）
    background_generation: bool  # 后台任务生成模式（无用户交互，不进入追问澄清）

    # ==================== 题目相关 ====================
    quiz_config: Optional[Dict[str, Any]]  # 题目生成配置
    quiz_questions: Optional[List[Dict[str, Any]]]  # 生成的题目
    quiz_answer: Optional[str]  # 用户提交的答案
    quiz_result: Optional[Dict[str, Any]]  # 题目判定结果

    # ==================== 流式输出控制 ====================
    stream_events: Annotated[List[Dict[str, Any]], operator.add]  # 流式事件队列
    current_step: Annotated[str, reduce_current_step]  # 当前处理步骤描述（带并发合并Redurcer）
    error: Annotated[Optional[str], reduce_error]  # 错误信息（带并发合并Reducer）
    sse_callback: Any  # Callable[[str], None] - 实时推送 SSE 事件的回调函数
    create_placeholder_callback: Any  # Callable[[list], dict] - 创建占位资源记录的回调函数

    # ==================== 智能体自主异常检测 ====================
    agent_anomaly: bool  # 智能体自主检测到内容偏离/异常，需中断回主控
    anomaly_reason: str  # 异常原因描述
    anomaly_clarify: bool  # 主控已处理异常，简答智能体进入追问澄清模式

    # ==================== 循环控制 ====================
    iteration_count: int  # 当前迭代次数（防止无限循环）
    max_iterations: int  # 最大迭代次数


# ==================== API 请求/响应模型 ====================

class ChatRequest(BaseModel):
    """对话请求"""
    user_id: int
    plan_id: Optional[int] = None
    session_id: str
    message: str
    human_feedback: Optional[str] = None  # 人工确认/补充反馈

class StreamEvent(BaseModel):
    """SSE 流式事件"""
    event_type: Literal[
        "thinking",       # 智能体思考中
        "intent",         # 意图识别结果
        "task_breakdown", # 任务分解结果
        "search_start",   # 开始检索
        "search_results", # 检索结果
        "review",         # 审查结果
        "content",        # 内容输出（流式文本）
        "module",         # 学习资源模块
        "quiz",           # 题目
        "quiz_result",    # 题目判定
        "profile_update", # 画像更新
        "confirm_needed", # 需要用户确认
        "error",          # 错误
        "done",           # 完成
    ]
    agent: str  # 产生事件的智能体名称
    data: Dict[str, Any]
    step_description: str = ""


class TaskBreakdownResult(BaseModel):
    """任务分解结果"""
    title: str
    description: str
    modules: List[Dict[str, Any]]  # 分解后的模块列表
    estimated_duration: str  # 预估时长
    difficulty_level: str  # 难度等级
    prerequisites: List[str]  # 前置知识


class QuizQuestion(BaseModel):
    """题目"""
    question_type: Literal["single_choice", "multiple_choice", "true_false", "fill_blank", "short_answer"]
    question_text: str
    options: Optional[List[str]] = None  # 选择题选项
    correct_answer: str
    explanation: str
    difficulty: int = Field(ge=1, le=5)
    knowledge_point: str  # 关联知识点


class ResourceModule(BaseModel):
    """学习资源模块"""
    module_type: str  # text, image, diagram, video, code, quiz
    title: str
    content: Any  # JSON 或 Markdown
    order: int
    metadata: Dict[str, Any] = {}
