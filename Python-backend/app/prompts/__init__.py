"""系统提示词集中管理 — 与智能体代码分离，便于维护和调优"""

from app.prompts.controller import CONTROLLER_PROMPT
from app.prompts.task_decomposer import TASK_DECOMPOSER_PROMPT
from app.prompts.simple_answer import SIMPLE_ANSWER_PROMPT
from app.prompts.rag_retriever import RAG_RETRIEVER_QUERY_OPTIMIZER_PROMPT
from app.prompts.content_orchestrator import (
    CONTENT_ORCHESTRATOR_BATCH_PROMPT,
    CONTENT_ORCHESTRATOR_PARALLEL_PROMPT,
)
from app.prompts.reviewer import REVIEWER_BATCH_PROMPT, REVIEWER_MODULE_PROMPT
from app.prompts.resource_generator import (
    RESOURCE_GENERATOR_PROMPT,
    SEARCH_PLANNING_PROMPT,
)
from app.prompts.enhanced_search_prompts import (
    REACT_SEARCH_SYSTEM_PROMPT,
    CONTENT_GENERATION_WITH_SOURCES_PROMPT,
)
from app.prompts.resource_type_generator import (
    RESOURCE_TYPE_GENERATOR_PROMPTS,
    RESOURCE_TYPE_GENERATOR_DEFAULT_PROMPT,
)
from app.prompts.quiz_generator import QUIZ_GENERATOR_PROMPT
from app.prompts.quiz_grader import QUIZ_GRADER_PROMPT
from app.prompts.profile_maintainer import PROFILE_MAINTAINER_PROMPT
from app.prompts.anomaly_checker import ANOMALY_CHECK_PROMPT
from app.prompts.qwen_chat import QWEN_CHAT_SYSTEM_PROMPT
