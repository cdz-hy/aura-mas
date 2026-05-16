"""
审查智能体 - 支持模块级别的内容审查
- 批量模式：检查整体 RAG 检索内容
- 模块模式：逐个检查已生成的模块内容，标记不通过的模块
"""
import logging
import asyncio
from typing import Dict, Any, List
from app.agents.schemas import AgentState
from app.agents.llm_factory import get_reviewer_llm
from app.prompts import REVIEWER_BATCH_PROMPT, REVIEWER_MODULE_PROMPT
from app.utils.token_recorder import record

logger = logging.getLogger("agents.reviewer")

def _flush_review_usage(review_results: list, user_id: int, scene: str, task_id=None,
                         extra_records: list = None):
    """收集审查过程中的 token 消耗并统一记录"""
    all_records = list(extra_records or [])
    for r in review_results:
        if isinstance(r, dict):
            records = r.pop("_usage_records", None) or []
            all_records.extend(records)
    for rec in all_records:
        record(
            user_id=user_id,
            scene=scene,
            model_name=rec["model"],
            input_tokens=rec["input_tokens"],
            output_tokens=rec["output_tokens"],
            task_id=task_id,
        )



def _review_single_module(
    module: Dict[str, Any],
    module_order: int,
    task_breakdown_module: Dict[str, Any],
) -> Dict[str, Any]:
    """
    审查单个模块的内容质量
    
    Args:
        module: 生成的模块内容
        module_order: 模块顺序
        task_breakdown_module: 任务分解中的模块信息（包含预期的关键点）
    
    Returns:
        审查结果
    """
    llm = get_reviewer_llm()
    
    module_title = module.get("title", "")
    module_content = module.get("content", "")
    module_type = module.get("module_type", "text")
    expected_key_points = task_breakdown_module.get("key_points", [])
    
    messages = [
        {"role": "system", "content": REVIEWER_MODULE_PROMPT},
        {"role": "user", "content": f"""模块信息:
- 标题: {module_title}
- 类型: {module_type}
- 预期关键点: {', '.join(expected_key_points)}

模块内容:
{module_content[:1500]}

请审查该模块的内容质量，输出 JSON:"""}
    ]
    
    try:
        result = llm.chat_json(messages, max_tokens=1536)
        result["module_order"] = module_order
        result["module_title"] = module_title
        result["_usage_records"] = llm.get_usage_records()
        return result
    except Exception as e:
        logger.error(f"  [模块{module_order}] 审查失败: {str(e)}")
        return {
            "module_order": module_order,
            "module_title": module_title,
            "passed": False,
            "score": 0,
            "issues": [{"severity": "critical", "description": f"审查过程异常: {str(e)}", "suggestion": "重新审查该模块"}],
            "feedback": f"审查异常: {str(e)}",
            "missing_points": [],
            "error": str(e),
        }


def reviewer_node(state: AgentState) -> Dict[str, Any]:
    """
    审查智能体节点
    
    支持两种模式：
    1. 批量模式：检查 RAG 检索内容（编排前）
    2. 模块模式：逐个检查已生成的模块内容（编排后）
    """
    rag_chunks = state.get("rag_context_chunks", [])
    user_message = state.get("user_message", "")
    learning_goal = state.get("learning_goal", user_message)
    module_list = state.get("module_list", [])
    task_breakdown = state.get("task_breakdown", {})
    
    # 判断使用哪种模式
    use_module_review = len(module_list) > 0
    
    logger.info(f"{'='*60}")
    logger.info(f"  [审查智能体] 开始处理")
    logger.info(f"  审查模式: {'模块级别' if use_module_review else '批量RAG'}")
    logger.info(f"  学习目标: {learning_goal[:100]}")
    
    # 模块级别审查
    if use_module_review:
        result = _review_modules(module_list, task_breakdown, learning_goal)
        extra_records = result.pop("_usage_records", None) or []
        _flush_review_usage(
            result.get("module_review_results", []),
            state.get("user_id", 0),
            "content_review", state.get("task_id"),
            extra_records=extra_records)
        return result
    
    # 批量 RAG 审查（原有逻辑）
    result = _review_rag_content(rag_chunks, learning_goal)
    extra_records = result.pop("_usage_records", None) or []
    _flush_review_usage([], state.get("user_id", 0),
                        "content_review", state.get("task_id"),
                        extra_records=extra_records)
    return result


def _review_modules(
    module_list: List[Dict[str, Any]],
    task_breakdown: Dict[str, Any],
    learning_goal: str,
) -> Dict[str, Any]:
    """模块级别审查：逐个检查已生成的模块"""
    logger.info(f"  待审查模块数: {len(module_list)} 个")
    
    task_modules = task_breakdown.get("modules", [])
    
    # 并发审查所有模块
    async def run_parallel_review():
        loop = asyncio.get_event_loop()
        
        tasks = []
        for i, module in enumerate(module_list):
            # 找到对应的任务分解模块
            task_module = task_modules[i] if i < len(task_modules) else {}
            
            task = loop.run_in_executor(
                None,
                _review_single_module,
                module,
                i + 1,
                task_module,
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        review_results = loop.run_until_complete(run_parallel_review())
        loop.close()
        
        # 处理审查结果
        failed_modules = []
        passed_modules = []
        all_issues = []
        total_score = 0
        
        for i, result in enumerate(review_results):
            if isinstance(result, Exception):
                logger.error(f"  [模块{i+1}] 审查异常: {str(result)}")
                failed_modules.append({
                    "module_order": i + 1,
                    "module_title": module_list[i].get("title", f"模块{i+1}") if i < len(module_list) else f"模块{i+1}",
                    "score": 0,
                    "issues": [{"severity": "critical", "description": f"审查异常: {str(result)}", "suggestion": "重新审查"}],
                    "feedback": f"审查异常: {str(result)}",
                    "missing_points": [],
                })
                continue
            
            module_order = result.get("module_order", i + 1)
            module_title = result.get("module_title", f"模块{module_order}")
            passed = result.get("passed", True)
            score = result.get("score", 0)
            issues = result.get("issues", [])
            feedback = result.get("feedback", "")
            missing_points = result.get("missing_points", [])
            
            total_score += score
            
            if not passed:
                failed_modules.append({
                    "module_order": module_order,
                    "module_title": module_title,
                    "score": score,
                    "issues": issues,
                    "feedback": feedback,
                    "missing_points": missing_points,
                })
                logger.warning(f"  [模块{module_order}] 未通过 (评分: {score}/100)")
                logger.warning(f"    反馈: {feedback[:100]}")
                if missing_points:
                    logger.warning(f"    缺失要点: {', '.join(missing_points)}")
            else:
                passed_modules.append(module_order)
                logger.info(f"  [模块{module_order}] 通过 (评分: {score}/100)")
            
            all_issues.extend(issues)
        
        # 计算整体结果
        avg_score = total_score / len(module_list) if module_list else 0
        overall_passed = len(failed_modules) == 0
        
        logger.info(f"  [审查智能体] 模块审查完成!")
        logger.info(f"    整体结果: {'全部通过' if overall_passed else f'{len(failed_modules)} 个模块未通过'}")
        logger.info(f"    平均评分: {avg_score:.1f}/100")
        logger.info(f"    通过模块: {passed_modules}")
        if failed_modules:
            logger.info(f"    未通过模块: {[m['module_order'] for m in failed_modules]}")
        logger.info(f"{'='*60}")
        
        return {
            "review_passed": overall_passed,
            "review_feedback": f"{'全部模块通过审查' if overall_passed else f'{len(failed_modules)} 个模块未通过审查'}",
            "review_suggestions": [m["feedback"] for m in failed_modules],
            "failed_modules": failed_modules,  # 新增：未通过的模块列表
            "passed_modules": passed_modules,  # 新增：通过的模块列表
            "module_review_results": review_results,  # 新增：所有模块的详细审查结果
            "current_step": f"审查智能体: {'全部通过' if overall_passed else f'{len(failed_modules)}/{len(module_list)} 个模块未通过'} (平均分: {avg_score:.1f})",
            "stream_events": [{
                "event_type": "review",
                "agent": "reviewer",
                "data": {
                    "passed": overall_passed,
                    "mode": "module",
                    "total_modules": len(module_list),
                    "failed_count": len(failed_modules),
                    "failed_modules": failed_modules,
                    "average_score": avg_score,
                },
                "step_description": f"模块审查完成: {len(failed_modules)}/{len(module_list)} 个未通过"
            }],
        }
        
    except Exception as e:
        logger.error(f"  [审查智能体] 模块审查异常: {str(e)}，默认不通过")
        logger.info(f"{'='*60}")
        return {
            "review_passed": False,
            "review_feedback": f"模块审查异常: {str(e)}",
            "review_suggestions": ["审查异常，建议重试"],
            "failed_modules": [{"module_order": i + 1, "module_title": m.get("title", f"模块{i+1}"), "score": 0} for i, m in enumerate(module_list)],
            "passed_modules": [],
            "current_step": f"审查智能体: 异常({str(e)}), 默认不通过",
            "stream_events": [{
                "event_type": "review",
                "agent": "reviewer",
                "data": {"passed": False, "error": str(e)},
                "step_description": "审查异常，默认不通过"
            }],
        }


def _review_rag_content(
    rag_chunks: List[Dict[str, Any]],
    learning_goal: str,
) -> Dict[str, Any]:
    """批量 RAG 审查：检查检索内容的整体质量（原有逻辑）"""
    logger.info(f"  待审查内容块: {len(rag_chunks)} 个")
    
    if not rag_chunks:
        logger.warning(f"  [审查智能体] 无内容可审查")
        logger.info(f"{'='*60}")
        return {
            "review_passed": False,
            "review_feedback": "无检索内容可供审查",
            "review_suggestions": ["重新检索"],
            "failed_modules": [],
            "passed_modules": [],
            "current_step": "审查智能体: 无内容可审查",
            "stream_events": [{
                "event_type": "review",
                "agent": "reviewer",
                "data": {"passed": False, "reason": "无检索内容"},
                "step_description": "审查完成：无内容可审查"
            }],
        }

    llm = get_reviewer_llm()

    content_summary = []
    for i, chunk in enumerate(rag_chunks[:15]):
        chunk_type = chunk.get("type", "text")
        heading = " > ".join(chunk.get("heading", []))
        doc_title = chunk.get("doc_title", "")
        if chunk_type == "image":
            content_summary.append(f"[{i+1}] [图片] 来源: {doc_title} | 章节: {heading} | 描述: {chunk.get('image_caption', '')[:200]}")
        else:
            content = chunk.get("content", "")[:300]
            content_summary.append(f"[{i+1}] [文本] 来源: {doc_title} | 章节: {heading} | 内容: {content}")

    messages = [
        {"role": "system", "content": REVIEWER_BATCH_PROMPT},
        {"role": "user", "content": f"""学习目标: {learning_goal}

检索到的知识内容:
{chr(10).join(content_summary)}

请对以上内容进行审查，输出 JSON:"""}
    ]

    try:
        logger.info(f"  [审查智能体] 正在调用 LLM 进行内容审查...")
        result = llm.chat_json(messages)
        passed = result.get("passed", True)
        issues = result.get("issues", [])
        suggestions = result.get("suggestions", [])
        summary = result.get("summary", "")
        score = result.get("overall_score", 0)

        critical_issues = [i for i in issues if i.get("severity") == "critical"]
        warning_issues = [i for i in issues if i.get("severity") == "warning"]

        logger.info(f"  [审查智能体] 审查完成!")
        logger.info(f"    结果: {'通过' if passed else '未通过'}")
        logger.info(f"    评分: {score}/100")
        logger.info(f"    问题数: {len(issues)} (严重: {len(critical_issues)}, 警告: {len(warning_issues)})")
        for issue in issues:
            logger.info(f"      [{issue.get('severity')}] {issue.get('description', '')[:80]}")
        if suggestions:
            logger.info(f"    优化建议: {', '.join(suggestions[:3])}")
        logger.info(f"    总结: {summary[:150]}")
        logger.info(f"{'='*60}")

        return {
            "_usage_records": llm.get_usage_records(),
            "review_passed": passed,
            "review_feedback": summary,
            "review_suggestions": suggestions,
            "failed_modules": [],
            "passed_modules": [],
            "current_step": f"审查智能体: {'通过' if passed else '未通过'} (评分: {score}, 关键问题: {len(critical_issues)})",
            "stream_events": [{
                "event_type": "review",
                "agent": "reviewer",
                "data": {
                    "passed": passed,
                    "mode": "batch",
                    "score": score,
                    "issues": issues,
                    "suggestions": suggestions,
                    "summary": summary,
                },
                "step_description": f"审查{'通过' if passed else '未通过'}: {summary[:100]}"
            }],
        }

    except Exception as e:
        logger.error(f"  [审查智能体] 审查异常: {str(e)}，默认不通过")
        logger.info(f"{'='*60}")
        return {
            "review_passed": False,
            "review_feedback": f"审查过程异常: {str(e)}",
            "review_suggestions": ["审查异常，建议重试检索"],
            "failed_modules": [],
            "passed_modules": [],
            "current_step": f"审查智能体: 异常({str(e)}), 默认不通过",
            "stream_events": [{
                "event_type": "review",
                "agent": "reviewer",
                "data": {"passed": False, "error": str(e)},
                "step_description": "审查异常，默认不通过"
            }],
        }
