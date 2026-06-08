"""RAG 检索词优化测试"""
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

retrieval = ModuleType("app.services.retrieval")
retrieval.HybridRetrievalService = object
sys.modules.setdefault("app.services.retrieval", retrieval)

from app.agents.rag_retriever import _optimize_search_queries


def test_optimize_search_queries_records_token_usage_without_free_state_variable():
    llm = MagicMock()
    llm.chat_json.return_value = {"queries": ["NLP 文本分类 序列标注 实践"]}

    with patch("app.agents.rag_retriever.record_from_mimo") as record:
        queries = _optimize_search_queries(
            [{"title": "NLP核心任务实践", "description": "从文本分类到序列标注"}],
            "请生成学习资源",
            llm,
            user_id=1,
            task_id=36,
        )

    assert queries == ["NLP 文本分类 序列标注 实践"]
    record.assert_called_once_with(llm, 1, "rag_query_optimization", 36)
