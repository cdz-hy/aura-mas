/**
 * 用户画像问题数据
 * 44道题，4个维度，每个维度11道题
 *
 * 维度说明：
 * - active_vs_reflective: 活跃型 vs 沉思型
 * - sensing_vs_intuitive: 感官型 vs 直觉型
 * - visual_vs_verbal: 视觉型 vs 言语型
 * - sequential_vs_global: 序列型 vs 全局型
 *
 * 计分规则：
 * - 选 A = +1 分，选 B = -1 分
 * - 正数偏向维度前半类，负数偏向维度后半类
 */

export type ProfileDimension =
  | 'active_vs_reflective'
  | 'sensing_vs_intuitive'
  | 'visual_vs_verbal'
  | 'sequential_vs_global'

export interface ProfileQuestion {
  id: number
  dimension: ProfileDimension
  question: string
  optionA: string
  optionB: string
  /** 选择A时对该维度的影响方向：+1 表示偏向维度前半类，-1 表示偏向维度后半类 */
  scoreA: 1 | -1
}

export const profileQuestions: ProfileQuestion[] = [
  // ========== 活跃/沉思 (Active vs Reflective) ==========
  {
    id: 1,
    dimension: 'active_vs_reflective',
    question: '为了理解一件事，你更愿意：',
    optionA: '动手实操',
    optionB: '静心思考',
    scoreA: 1
  },
  {
    id: 5,
    dimension: 'active_vs_reflective',
    question: '学习新知识最好的方式：',
    optionA: '和别人讨论分享',
    optionB: '独自琢磨梳理',
    scoreA: 1
  },
  {
    id: 9,
    dimension: 'active_vs_reflective',
    question: '小组学习时你更习惯：',
    optionA: '主动发言、参与讨论',
    optionB: '安静倾听，事后复盘',
    scoreA: 1
  },
  {
    id: 13,
    dimension: 'active_vs_reflective',
    question: '遇到困惑你会：',
    optionA: '立刻找人交流探讨',
    optionB: '自己反复思考直到理清',
    scoreA: 1
  },
  {
    id: 17,
    dimension: 'active_vs_reflective',
    question: '复习知识点你喜欢：',
    optionA: '给别人讲解输出',
    optionB: '自己默默梳理笔记',
    scoreA: 1
  },
  {
    id: 21,
    dimension: 'active_vs_reflective',
    question: '吸收新知识的最佳场景：',
    optionA: '小组研讨、课堂互动',
    optionB: '独自安静自学',
    scoreA: 1
  },
  {
    id: 25,
    dimension: 'active_vs_reflective',
    question: '遇到不懂的内容：',
    optionA: '立刻提问、交换想法',
    optionB: '先自己钻研很久再求助',
    scoreA: 1
  },
  {
    id: 29,
    dimension: 'active_vs_reflective',
    question: '课堂上你更倾向：',
    optionA: '主动参与互动、发言',
    optionB: '安静听课，课后消化',
    scoreA: 1
  },
  {
    id: 33,
    dimension: 'active_vs_reflective',
    question: '掌握知识后，你希望：',
    optionA: '和他人分享讲解',
    optionB: '自己内化沉淀',
    scoreA: 1
  },
  {
    id: 37,
    dimension: 'active_vs_reflective',
    question: '巩固知识你会：',
    optionA: '做练习、实操输出',
    optionB: '复盘笔记、深度思考',
    scoreA: 1
  },
  {
    id: 41,
    dimension: 'active_vs_reflective',
    question: '新知识入门：',
    optionA: '通过实践、讨论入门',
    optionB: '通过阅读、思考入门',
    scoreA: 1
  },

  // ========== 感悟/直觉 (Sensing vs Intuitive) ==========
  {
    id: 2,
    dimension: 'sensing_vs_intuitive',
    question: '别人更愿意形容你：',
    optionA: '务实严谨',
    optionB: '创新脑洞',
    scoreA: 1
  },
  {
    id: 6,
    dimension: 'sensing_vs_intuitive',
    question: '如果你是老师，你更喜欢教：',
    optionA: '事实、实操类课程',
    optionB: '理论、概念类课程',
    scoreA: 1
  },
  {
    id: 10,
    dimension: 'sensing_vs_intuitive',
    question: '做题时你更喜欢：',
    optionA: '成熟固定解法',
    optionB: '尝试全新思路',
    scoreA: 1
  },
  {
    id: 14,
    dimension: 'sensing_vs_intuitive',
    question: '你更容易记住：',
    optionA: '客观事实、数据',
    optionB: '底层规律、逻辑关系',
    scoreA: 1
  },
  {
    id: 18,
    dimension: 'sensing_vs_intuitive',
    question: '面对考题你更适应：',
    optionA: '课堂讲过的固定题型',
    optionB: '灵活拓展、需要推导的题型',
    scoreA: 1
  },
  {
    id: 22,
    dimension: 'sensing_vs_intuitive',
    question: '你更信任：',
    optionA: '真实可落地的经验',
    optionB: '逻辑自洽的抽象理论',
    scoreA: 1
  },
  {
    id: 26,
    dimension: 'sensing_vs_intuitive',
    question: '你更擅长：',
    optionA: '标准化实操、记忆细节',
    optionB: '抽象建模、创新推导',
    scoreA: 1
  },
  {
    id: 30,
    dimension: 'sensing_vs_intuitive',
    question: '思考问题你优先：',
    optionA: '现实可行的方案',
    optionB: '全新可能性、创新思路',
    scoreA: 1
  },
  {
    id: 34,
    dimension: 'sensing_vs_intuitive',
    question: '我认为更重要的是：',
    optionA: '落地实践、客观事实',
    optionB: '底层原理、内在关联',
    scoreA: 1
  },
  {
    id: 38,
    dimension: 'sensing_vs_intuitive',
    question: '我反感课程：',
    optionA: '全是抽象理论，无现实案例',
    optionB: '大量机械重复计算背诵',
    scoreA: 1
  },
  {
    id: 42,
    dimension: 'sensing_vs_intuitive',
    question: '做题思路：',
    optionA: '按固定步骤推导',
    optionB: '凭全局直觉快速找到突破口',
    scoreA: 1
  },

  // ========== 视觉/言语 (Visual vs Verbal) ==========
  {
    id: 3,
    dimension: 'visual_vs_verbal',
    question: '回忆昨天的事，你更容易：',
    optionA: '脑海浮现画面',
    optionB: '用文字描述',
    scoreA: 1
  },
  {
    id: 7,
    dimension: 'visual_vs_verbal',
    question: '获取信息你偏爱：',
    optionA: '图表、流程图、图片',
    optionB: '文字、口头讲解',
    scoreA: 1
  },
  {
    id: 11,
    dimension: 'visual_vs_verbal',
    question: '看书学习，你会重点关注：',
    optionA: '配图、示意图',
    optionB: '文字段落',
    scoreA: 1
  },
  {
    id: 15,
    dimension: 'visual_vs_verbal',
    question: '听完一堂课，你印象最深的是：',
    optionA: '板书、示意图',
    optionB: '老师讲的文字内容',
    scoreA: 1
  },
  {
    id: 19,
    dimension: 'visual_vs_verbal',
    question: '做笔记你习惯：',
    optionA: '大量画图、思维导图',
    optionB: '纯文字段落记录',
    scoreA: 1
  },
  {
    id: 23,
    dimension: 'visual_vs_verbal',
    question: '学习工具你首选：',
    optionA: '流程图、可视化图表',
    optionB: '文档、文字讲义',
    scoreA: 1
  },
  {
    id: 27,
    dimension: 'visual_vs_verbal',
    question: '记知识点你依赖：',
    optionA: '图形、颜色、可视化标记',
    optionB: '文字定义、段落总结',
    scoreA: 1
  },
  {
    id: 31,
    dimension: 'visual_vs_verbal',
    question: '记忆内容：',
    optionA: '图片、曲线、架构图',
    optionB: '定义、公式、文字描述',
    scoreA: 1
  },
  {
    id: 35,
    dimension: 'visual_vs_verbal',
    question: '教材你更喜欢：',
    optionA: '图文并茂，示意图丰富',
    optionB: '文字详实，配图较少',
    scoreA: 1
  },
  {
    id: 39,
    dimension: 'visual_vs_verbal',
    question: '复习时你会：',
    optionA: '手绘思维导图、结构图',
    optionB: '整理文字提纲、摘抄重点',
    scoreA: 1
  },
  {
    id: 43,
    dimension: 'visual_vs_verbal',
    question: '学习规划：',
    optionA: '拆分每日小任务循序渐进',
    optionB: '先定大目标，零散推进',
    scoreA: 1
  },

  // ========== 序列/全局 (Sequential vs Global) ==========
  {
    id: 4,
    dimension: 'sequential_vs_global',
    question: '学习时你习惯：',
    optionA: '先吃透细节再懂整体',
    optionB: '先看懂全貌再补细节',
    scoreA: 1
  },
  {
    id: 8,
    dimension: 'sequential_vs_global',
    question: '弄懂一件事的逻辑：',
    optionA: '搞懂每个部分就能懂整体',
    optionB: '看懂整体才能理解局部',
    scoreA: 1
  },
  {
    id: 12,
    dimension: 'sequential_vs_global',
    question: '遇到复杂知识点：',
    optionA: '按步骤一点点拆解',
    optionB: '先抓整体框架再细化',
    scoreA: 1
  },
  {
    id: 16,
    dimension: 'sequential_vs_global',
    question: '学习新领域，你会：',
    optionA: '从基础小节依次学起',
    optionB: '先通读全貌建立认知',
    scoreA: 1
  },
  {
    id: 20,
    dimension: 'sequential_vs_global',
    question: '解决难题你会：',
    optionA: '分步推导、逐步验证',
    optionB: '凭整体直觉一次性突破',
    scoreA: 1
  },
  {
    id: 24,
    dimension: 'sequential_vs_global',
    question: '梳理知识体系：',
    optionA: '逐个模块串联拼接',
    optionB: '先搭建顶层框架再填充',
    scoreA: 1
  },
  {
    id: 28,
    dimension: 'sequential_vs_global',
    question: '理解复杂系统：',
    optionA: '逐个拆解组件弄懂',
    optionB: '先看懂整体运行逻辑',
    scoreA: 1
  },
  {
    id: 32,
    dimension: 'sequential_vs_global',
    question: '知识串联：',
    optionA: '按章节顺序逐步关联',
    optionB: '跨章节、跨领域整体串联',
    scoreA: 1
  },
  {
    id: 36,
    dimension: 'sequential_vs_global',
    question: '学习进度：',
    optionA: '稳步线性推进，不跳章节',
    optionB: '跳读，先看感兴趣的章节',
    scoreA: 1
  },
  {
    id: 40,
    dimension: 'sequential_vs_global',
    question: '别人更愿意形容你：',
    optionA: '务实严谨',
    optionB: '创新脑洞',
    scoreA: 1
  },
  {
    id: 44,
    dimension: 'sequential_vs_global',
    question: '面对新任务：',
    optionA: '制定详细计划逐步执行',
    optionB: '先动手做，边做边调整',
    scoreA: 1
  }
]

/** 维度中文名称映射 */
export const dimensionLabels: Record<ProfileDimension, { positive: string; negative: string }> = {
  active_vs_reflective: { positive: '活跃型', negative: '沉思型' },
  sensing_vs_intuitive: { positive: '感官型', negative: '直觉型' },
  visual_vs_verbal: { positive: '视觉型', negative: '言语型' },
  sequential_vs_global: { positive: '序列型', negative: '全局型' }
}

/** 本地存储 key */
export const ANSWERED_QUESTIONS_KEY = 'profile_answered_questions'
