"""
用户画像工具函数
确保 learning_behavior 字段结构完整，与前端显示匹配
"""
from typing import Dict, Any


def get_default_learning_behavior() -> Dict[str, Any]:
    """
    获取默认的用户画像 learning_behavior 结构
    
    所有字段初始化为空或0，随着用户交互逐步完善
    """
    return {
        # Felder-Silverman 学习风格维度 (范围: -1.0 ~ +1.0)
        "visual_vs_verbal": 0.0,          # 视觉型(-1) ↔ 言语型(+1)
        "active_vs_reflective": 0.0,      # 活跃型(-1) ↔ 沉思型(+1)
        "sensing_vs_intuitive": 0.0,      # 感官型(-1) ↔ 直觉型(+1)
        "sequential_vs_global": 0.0,      # 序列型(-1) ↔ 全局型(+1)
        
        # 知识与能力
        "knowledge_base": [],              # 已掌握的知识领域
        "weak_areas": [],                  # 薄弱知识点
        "interest_tags": [],               # 兴趣标签
        
        # 学习偏好
        "preferred_resource_types": [],    # 偏好的资源类型
        "goal_orientation": "career",      # 目标导向: career/exam/interest/skill
        
        # 扩展字段（可选，根据用户行为自动分析）
        "learning_speed": 0.5,             # 学习速度评分 (0-1)
        "engagement_level": 0.5,           # 参与度评分 (0-1)
        "preferred_difficulty": 3,         # 偏好难度 (1-5)
        "quiz_accuracy": 0.0,              # 答题准确率 (0-1)
        "completion_rate": 0.0,            # 完成率 (0-1)
    }


def ensure_learning_behavior_fields(learning_behavior: Dict[str, Any]) -> Dict[str, Any]:
    """
    确保 learning_behavior 包含所有必需字段
    
    如果缺少字段，自动补充默认值
    保持现有字段的值不变
    
    Args:
        learning_behavior: 原始的 learning_behavior 字典
        
    Returns:
        补充完整后的 learning_behavior 字典
    """
    if not learning_behavior:
        return get_default_learning_behavior()
    
    default = get_default_learning_behavior()
    
    # 补充缺失的字段
    for key, default_value in default.items():
        if key not in learning_behavior:
            learning_behavior[key] = default_value
    
    # 确保学习风格维度在有效范围内
    for dimension in ["visual_vs_verbal", "active_vs_reflective", "sensing_vs_intuitive", "sequential_vs_global"]:
        if dimension in learning_behavior:
            value = learning_behavior[dimension]
            if isinstance(value, (int, float)):
                learning_behavior[dimension] = max(-1.0, min(1.0, float(value)))
            else:
                learning_behavior[dimension] = 0.0
    
    # 确保列表字段是列表类型
    for list_field in ["knowledge_base", "weak_areas", "interest_tags", "preferred_resource_types"]:
        if list_field in learning_behavior:
            if not isinstance(learning_behavior[list_field], list):
                learning_behavior[list_field] = []
    
    return learning_behavior


def map_dimension_name(dimension: str) -> str:
    """
    将简答智能体的维度名称映射到标准字段名
    
    Args:
        dimension: 简答智能体使用的维度名称
        
    Returns:
        标准的字段名称
    """
    mapping = {
        "visual_verbal": "visual_vs_verbal",
        "active_reflective": "active_vs_reflective",
        "sensing_intuitive": "sensing_vs_intuitive",
        "sequential_global": "sequential_vs_global",
        "knowledge_base": "knowledge_base",
        "content_preference": "preferred_resource_types",
        "quiz_preference": "preferred_resource_types",
    }
    return mapping.get(dimension, dimension)


def update_learning_behavior(
    current: Dict[str, Any],
    updates: Dict[str, Any],
    confidence: float = 1.0
) -> Dict[str, Any]:
    """
    更新用户画像的 learning_behavior

    Args:
        current: 当前的 learning_behavior
        updates: 需要更新的字段和值
            - 学习风格维度: 增量调整（累加到当前值）
            - 列表字段: 期望的最终状态（直接替换）
        confidence: 更新的置信度 (0-1)，用于调整学习风格维度的变化幅度

    Returns:
        更新后的 learning_behavior
    """
    # 确保当前画像字段完整
    current = ensure_learning_behavior_fields(current)
    
    for key, value in updates.items():
        if value is None:
            continue
        
        # 映射字段名
        key = map_dimension_name(key)
        
        # 学习风格维度：渐进式调整
        if key in ["visual_vs_verbal", "active_vs_reflective", "sensing_vs_intuitive", "sequential_vs_global"]:
            if isinstance(value, (int, float)):
                current_value = current.get(key, 0.0)
                # 渐进式调整：新值 = 当前值 + (调整值 × 置信度)
                adjustment = value * confidence
                new_value = current_value + adjustment
                # 限制在 [-1, 1] 范围内
                current[key] = max(-1.0, min(1.0, new_value))
        
        # 列表字段：直接替换为 LLM 输出的期望最终状态
        elif key in ["knowledge_base", "weak_areas", "interest_tags", "preferred_resource_types"]:
            if isinstance(value, list):
                current[key] = value
            elif isinstance(value, str):
                current[key] = [value]
        
        # 其他字段：直接更新
        else:
            current[key] = value
    
    return current


def analyze_user_behavior(
    quiz_stats: Dict[str, Any] = None,
    session_data: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    根据用户行为数据自动分析并生成画像更新
    
    Args:
        quiz_stats: 答题统计数据
        session_data: 会话数据（学习时长、交互频率等）
        
    Returns:
        建议的画像更新字典
    """
    updates = {}
    
    # 分析答题数据
    if quiz_stats:
        total = quiz_stats.get("total_questions", 0)
        correct = quiz_stats.get("correct_count", 0)
        
        if total > 0:
            accuracy = correct / total
            updates["quiz_accuracy"] = accuracy
            
            # 根据准确率调整学习速度评分
            if total >= 10:  # 至少10题才有参考价值
                if accuracy >= 0.8:
                    updates["learning_speed"] = 0.8
                elif accuracy >= 0.6:
                    updates["learning_speed"] = 0.6
                else:
                    updates["learning_speed"] = 0.4
    
    # 分析会话数据
    if session_data:
        interaction_count = session_data.get("interaction_count", 0)
        session_duration = session_data.get("duration_minutes", 0)
        
        # 参与度评分
        if interaction_count > 0 and session_duration > 0:
            # 每分钟交互次数
            interactions_per_minute = interaction_count / session_duration
            if interactions_per_minute >= 2:
                updates["engagement_level"] = 0.9
            elif interactions_per_minute >= 1:
                updates["engagement_level"] = 0.7
            else:
                updates["engagement_level"] = 0.5
    
    return updates


def format_for_display(learning_behavior: Dict[str, Any]) -> Dict[str, Any]:
    """
    格式化用户画像用于前端显示
    
    Args:
        learning_behavior: 原始的 learning_behavior
        
    Returns:
        格式化后的数据，适合前端展示
    """
    learning_behavior = ensure_learning_behavior_fields(learning_behavior)
    
    return {
        # 学习风格雷达图数据
        "learning_style": {
            "visual_preference": abs(learning_behavior["visual_vs_verbal"]),
            "visual_type": "visual" if learning_behavior["visual_vs_verbal"] < 0 else "verbal",
            "active_preference": abs(learning_behavior["active_vs_reflective"]),
            "active_type": "active" if learning_behavior["active_vs_reflective"] < 0 else "reflective",
            "sensing_preference": abs(learning_behavior["sensing_vs_intuitive"]),
            "sensing_type": "sensing" if learning_behavior["sensing_vs_intuitive"] < 0 else "intuitive",
            "sequential_preference": abs(learning_behavior["sequential_vs_global"]),
            "sequential_type": "sequential" if learning_behavior["sequential_vs_global"] < 0 else "global",
        },
        
        # 知识标签云
        "knowledge_tags": {
            "mastered": learning_behavior["knowledge_base"],
            "interested": learning_behavior["interest_tags"],
            "weak": learning_behavior["weak_areas"],
        },
        
        # 学习偏好
        "preferences": {
            "resource_types": learning_behavior["preferred_resource_types"],
            "goal": learning_behavior["goal_orientation"],
            "difficulty": learning_behavior.get("preferred_difficulty", 3),
        },
        
        # 学习表现
        "performance": {
            "learning_speed": learning_behavior.get("learning_speed", 0.5),
            "engagement": learning_behavior.get("engagement_level", 0.5),
            "quiz_accuracy": learning_behavior.get("quiz_accuracy", 0.0),
            "completion_rate": learning_behavior.get("completion_rate", 0.0),
        }
    }
