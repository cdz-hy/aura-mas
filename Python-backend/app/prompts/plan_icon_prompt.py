"""
学习计划图标生成提示词
采用"选择+组合"模式，使用预定义的高质量图标模板
"""

# 预定义的高质量 SVG 图标库（基于 Lucide Icons 风格）
# 每个图标都是精心设计的 24x24 矢量图
ICON_LIBRARY = {
    # 编程与技术类
    "code": {
        "name": "代码",
        "svg": '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
        "keywords": ["编程", "代码", "开发", "python", "java", "javascript", "typescript", "c++", "golang", "rust", "程序", "coding"]
    },
    "terminal": {
        "name": "终端",
        "svg": '<rect x="2" y="3" width="20" height="18" rx="2" ry="2"/><polyline points="6 8 10 12 6 16"/><line x1="14" y1="16" x2="18" y2="16"/>',
        "keywords": ["终端", "命令行", "linux", "shell", "bash", "运维", "部署"]
    },
    "web": {
        "name": "网页",
        "svg": '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
        "keywords": ["前端", "网页", "web", "html", "css", "react", "vue", "angular", "浏览器", "网站"]
    },
    "database": {
        "name": "数据库",
        "svg": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>',
        "keywords": ["数据库", "sql", "mysql", "postgresql", "mongodb", "redis", "存储", "data"]
    },
    "api": {
        "name": "接口",
        "svg": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
        "keywords": ["api", "接口", "restful", "graphql", "微服务", "服务", "后端"]
    },
    
    # 数据与分析类
    "chart": {
        "name": "图表",
        "svg": '<path d="M3 3v18h18"/><path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3"/>',
        "keywords": ["数据", "分析", "统计", "图表", "可视化", "analytics", "dashboard", "报表"]
    },
    "bar_chart": {
        "name": "柱状图",
        "svg": '<line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/>',
        "keywords": ["柱状图", "统计", "对比", "分析"]
    },
    "pie_chart": {
        "name": "饼图",
        "svg": '<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>',
        "keywords": ["饼图", "占比", "比例", "分布"]
    },
    
    # AI 与机器学习类
    "brain": {
        "name": "大脑",
        "svg": '<path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2z"/>',
        "keywords": ["ai", "人工智能", "机器学习", "深度学习", "神经网络", "ml", "dl", "大模型", "llm", "gpt", "transformer"]
    },
    "cpu": {
        "name": "芯片",
        "svg": '<rect x="4" y="4" width="16" height="16" rx="2" ry="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>',
        "keywords": ["硬件", "芯片", "gpu", "计算", "cuda", "推理", "inference"]
    },
    "network": {
        "name": "神经网络",
        "svg": '<circle cx="12" cy="12" r="3"/><circle cx="6" cy="6" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/><line x1="10" y1="10" x2="7.5" y2="7.5"/><line x1="14" y1="10" x2="16.5" y2="7.5"/><line x1="10" y1="14" x2="7.5" y2="16.5"/><line x1="14" y1="14" x2="16.5" y2="16.5"/>',
        "keywords": ["神经网络", "网络", "节点", "图谱", "知识图谱", "graph"]
    },
    
    # 学习与教育类
    "book": {
        "name": "书本",
        "svg": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
        "keywords": ["学习", "书本", "阅读", "知识", "教程", "课程", "基础", "入门"]
    },
    "graduation_cap": {
        "name": "学位帽",
        "svg": '<path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 10 3 12 0v-5"/>',
        "keywords": ["学习", "教育", "毕业", "课程", "培训", "学校"]
    },
    "lightbulb": {
        "name": "灯泡",
        "svg": '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/>',
        "keywords": ["创意", "想法", "灵感", "思考", "设计", "创新"]
    },
    
    # 算法与数据结构类
    "algorithm": {
        "name": "算法",
        "svg": '<path d="M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z"/><path d="M10 6.5h4M6.5 10v4M17.5 10v4M10 17.5h4"/>',
        "keywords": ["算法", "排序", "搜索", "动态规划", "贪心", "递归", "algorithm"]
    },
    "tree": {
        "name": "树",
        "svg": '<circle cx="12" cy="5" r="2"/><circle cx="7" cy="12" r="2"/><circle cx="17" cy="12" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="9" cy="19" r="2"/><circle cx="15" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><line x1="12" y1="7" x2="7" y2="10"/><line x1="12" y1="7" x2="17" y2="10"/><line x1="7" y1="14" x2="5" y2="17"/><line x1="7" y1="14" x2="9" y2="17"/><line x1="17" y1="14" x2="15" y2="17"/><line x1="17" y1="14" x2="19" y2="17"/>',
        "keywords": ["树", "二叉树", "数据结构", "tree", "结构"]
    },
    "graph": {
        "name": "图",
        "svg": '<circle cx="5" cy="12" r="3"/><circle cx="19" cy="6" r="3"/><circle cx="19" cy="18" r="3"/><line x1="8" y1="11" x2="16" y2="7"/><line x1="8" y1="13" x2="16" y2="17"/>',
        "keywords": ["图", "图论", "图算法", "graph", "网络"]
    },
    
    # 系统与架构类
    "server": {
        "name": "服务器",
        "svg": '<rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/>',
        "keywords": ["服务器", "后端", "部署", "运维", "server", "云"]
    },
    "cloud": {
        "name": "云",
        "svg": '<path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>',
        "keywords": ["云", "云计算", "aws", "azure", "cloud", "容器", "docker", "kubernetes"]
    },
    "lock": {
        "name": "锁",
        "svg": '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
        "keywords": ["安全", "加密", "认证", "授权", "security", "加密", "密码"]
    },
    
    # 数学与理论类
    "math": {
        "name": "数学",
        "svg": '<path d="M3 3l6 6M9 3L3 9M14 8h6M17 5v6M3 16h4l3-4 3 4h4M3 21h18"/>',
        "keywords": ["数学", "线性代数", "概率", "统计", "微积分", "math"]
    },
    "calculator": {
        "name": "计算器",
        "svg": '<rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><line x1="8" y1="10" x2="8" y2="10.01"/><line x1="12" y1="10" x2="12" y2="10.01"/><line x1="16" y1="10" x2="16" y2="10.01"/><line x1="8" y1="14" x2="8" y2="14.01"/><line x1="12" y1="14" x2="12" y2="14.01"/><line x1="16" y1="14" x2="16" y2="14.01"/><line x1="8" y1="18" x2="8" y2="18.01"/><line x1="12" y1="18" x2="12" y2="18.01"/><line x1="16" y1="18" x2="16" y2="18.01"/>',
        "keywords": ["计算", "数学", "数值", "计算方法"]
    },
    
    # 工具与效率类
    "tool": {
        "name": "工具",
        "svg": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
        "keywords": ["工具", "工程", "配置", "环境", "工具链"]
    },
    "settings": {
        "name": "设置",
        "svg": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
        "keywords": ["配置", "设置", "系统", "运维"]
    },
    
    # 特定技术栈
    "python": {
        "name": "Python",
        "svg": '<path d="M9 3v4h6V3z"/><path d="M15 21v-4H9v4z"/><path d="M9 7a4 4 0 0 0-4 4v2a4 4 0 0 0 4 4h6a4 4 0 0 0 4-4v-2a4 4 0 0 0-4-4z"/><circle cx="10.5" cy="5" r="0.5" fill="currentColor"/><circle cx="13.5" cy="19" r="0.5" fill="currentColor"/>',
        "keywords": ["python", "爬虫", "自动化", "脚本"]
    },
    "java": {
        "name": "Java",
        "svg": '<path d="M10 17s-1.5 1 1 1c3 0 4.5-1 7-1"/><path d="M9 14s-1.5 1 1 1c3 0 5.5-1 8-1"/><path d="M12 3c-1 2-2 3-2 5 0 2.5 2 4 2 4s2-1.5 2-4c0-2-1-3-2-5z"/>',
        "keywords": ["java", "spring", "后端", "企业级"]
    },
    "database_sql": {
        "name": "SQL",
        "svg": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/><text x="7" y="11" font-size="4" fill="currentColor">SQL</text>',
        "keywords": ["sql", "查询", "数据库设计"]
    },
    
    # 前端框架与库
    "react": {
        "name": "React",
        "svg": '<circle cx="12" cy="12" r="2"/><ellipse cx="12" cy="12" rx="10" ry="4.5" transform="rotate(0 12 12)"/><ellipse cx="12" cy="12" rx="10" ry="4.5" transform="rotate(60 12 12)"/><ellipse cx="12" cy="12" rx="10" ry="4.5" transform="rotate(120 12 12)"/>',
        "keywords": ["react", "前端", "组件", "hooks", "jsx", "前端框架"]
    },
    "vue": {
        "name": "Vue",
        "svg": '<path d="M2 3l10 18L22 3h-4l-6 10.5L6 3z"/>',
        "keywords": ["vue", "前端", "响应式", "mvvm", "前端框架"]
    },
    "angular": {
        "name": "Angular",
        "svg": '<path d="M12 2L3 6l1.5 13L12 22l7.5-3L21 6z"/><path d="M12 6l-4 8h2l1-2h2l1 2h2z"/><path d="M11 10l1-2 1 2h-2z"/>',
        "keywords": ["angular", "前端", "typescript", "前端框架"]
    },
    
    # 后端框架
    "spring": {
        "name": "Spring",
        "svg": '<circle cx="12" cy="12" r="3"/><path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a5 5 0 0 0 10 0v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z"/><path d="M12 12v5"/>',
        "keywords": ["spring", "springboot", "java", "后端框架", "微服务"]
    },
    "django": {
        "name": "Django",
        "svg": '<rect x="3" y="3" width="8" height="18" rx="1"/><rect x="13" y="3" width="8" height="18" rx="1"/><line x1="7" y1="7" x2="7" y2="13"/><circle cx="17" cy="10" r="2"/>',
        "keywords": ["django", "python", "web框架", "后端", "orm"]
    },
    "flask": {
        "name": "Flask",
        "svg": '<path d="M10 2v7H8l4 10 4-10h-2V2z"/><circle cx="12" cy="21" r="1"/>',
        "keywords": ["flask", "python", "轻量级", "web", "微框架"]
    },
    "nodejs": {
        "name": "Node.js",
        "svg": '<path d="M12 2L3 7v10l9 5 9-5V7z"/><path d="M12 22V12"/><path d="M12 12L3 7"/><path d="M12 12l9-5"/>',
        "keywords": ["nodejs", "node", "javascript", "后端", "服务端", "npm"]
    },
    
    # 移动开发
    "mobile": {
        "name": "移动端",
        "svg": '<rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/>',
        "keywords": ["移动", "app", "android", "ios", "移动端", "手机"]
    },
    "flutter": {
        "name": "Flutter",
        "svg": '<path d="M14 2L4 12l4 4 14-14z"/><path d="M8 16l-4 4 4 4 8-8z"/>',
        "keywords": ["flutter", "dart", "跨平台", "移动开发"]
    },
    "android": {
        "name": "Android",
        "svg": '<circle cx="7" cy="9" r="1"/><circle cx="17" cy="9" r="1"/><path d="M5 13a7 7 0 0 0 14 0"/><path d="M12 4l-2-3M12 4l2-3"/><path d="M5 6h14a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z"/>',
        "keywords": ["android", "安卓", "移动开发", "kotlin"]
    },
    
    # 数据科学与机器学习
    "tensorflow": {
        "name": "TensorFlow",
        "svg": '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><path d="M10 6.5h4M6.5 10v4M17.5 10v4M10 17.5h4"/>',
        "keywords": ["tensorflow", "深度学习", "神经网络", "机器学习", "tf"]
    },
    "pytorch": {
        "name": "PyTorch",
        "svg": '<path d="M12 2L2 12l10 10 10-10z"/><circle cx="12" cy="12" r="3"/>',
        "keywords": ["pytorch", "深度学习", "机器学习", "神经网络", "torch"]
    },
    "pandas": {
        "name": "Pandas",
        "svg": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><circle cx="6.5" cy="6.5" r="1" fill="currentColor"/><circle cx="17.5" cy="17.5" r="1" fill="currentColor"/>',
        "keywords": ["pandas", "数据分析", "python", "dataframe", "数据处理"]
    },
    "jupyter": {
        "name": "Jupyter",
        "svg": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="8" r="1.5" fill="currentColor"/><circle cx="8" cy="16" r="1.5" fill="currentColor"/><circle cx="16" cy="16" r="1.5" fill="currentColor"/>',
        "keywords": ["jupyter", "notebook", "数据分析", "交互式", "python"]
    },
    
    # DevOps 与工具
    "docker": {
        "name": "Docker",
        "svg": '<rect x="2" y="6" width="3" height="3"/><rect x="6" y="6" width="3" height="3"/><rect x="10" y="6" width="3" height="3"/><rect x="2" y="10" width="3" height="3"/><rect x="6" y="10" width="3" height="3"/><rect x="10" y="10" width="3" height="3"/><rect x="6" y="2" width="3" height="3"/><path d="M14 10h7l-2 6H14z"/>',
        "keywords": ["docker", "容器", "部署", "devops", "镜像"]
    },
    "kubernetes": {
        "name": "Kubernetes",
        "svg": '<circle cx="12" cy="12" r="10"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/><path d="M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/>',
        "keywords": ["kubernetes", "k8s", "容器编排", "devops", "集群"]
    },
    "git": {
        "name": "Git",
        "svg": '<circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><circle cx="18" cy="6" r="3"/><line x1="9" y1="6" x2="15" y2="6"/><path d="M9 18a9 9 0 0 1 9-9"/>',
        "keywords": ["git", "版本控制", "github", "gitlab", "代码管理"]
    },
    "github": {
        "name": "GitHub",
        "svg": '<path d="M12 2C6.477 2 2 6.477 2 12c0 4.42 2.865 8.17 6.839 9.49.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.34-3.369-1.34-.454-1.156-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.831.092-.646.35-1.086.636-1.336-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0 1 12 6.836c.85.004 1.705.114 2.504.336 1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.203 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.578.688.48C19.138 20.167 22 16.418 22 12c0-5.523-4.477-10-10-10z"/>',
        "keywords": ["github", "开源", "代码托管", "git", "仓库"]
    },
    "ci_cd": {
        "name": "CI/CD",
        "svg": '<circle cx="6" cy="12" r="3"/><circle cx="18" cy="12" r="3"/><path d="M9 12h6"/><path d="M15 9l3 3-3 3"/>',
        "keywords": ["cicd", "持续集成", "持续部署", "自动化", "jenkins"]
    },
    
    # 测试
    "test_tube": {
        "name": "测试",
        "svg": '<path d="M14.5 2v16a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2V2"/><path d="M8.5 2h7"/><path d="M9.5 14h5"/>',
        "keywords": ["测试", "单元测试", "集成测试", "junit", "pytest", "test"]
    },
    "bug": {
        "name": "调试",
        "svg": '<path d="M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z"/><path d="M12 2v5M12 17v5M2 12h5M17 12h5"/><path d="M4.93 4.93l3.54 3.54M15.53 15.53l3.54 3.54M4.93 19.07l3.54-3.54M15.53 8.47l3.54-3.54"/>',
        "keywords": ["bug", "调试", "debug", "错误", "修复"]
    },
    
    # 通信与协议
    "wifi": {
        "name": "网络",
        "svg": '<path d="M5 12.55a11 11 0 0 1 14 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><circle cx="12" cy="20" r="1"/>',
        "keywords": ["网络", "通信", "http", "websocket", "协议"]
    },
    "message": {
        "name": "消息",
        "svg": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
        "keywords": ["消息", "聊天", "通信", "im", "chat"]
    },
    "mail": {
        "name": "邮件",
        "svg": '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>',
        "keywords": ["邮件", "email", "smtp", "通知"]
    },
    
    # 区块链与Web3
    "blockchain": {
        "name": "区块链",
        "svg": '<rect x="2" y="7" width="6" height="6" rx="1"/><rect x="9" y="7" width="6" height="6" rx="1"/><rect x="16" y="7" width="6" height="6" rx="1"/><path d="M8 10h1M15 10h1"/>',
        "keywords": ["区块链", "blockchain", "web3", "智能合约", "加密"]
    },
    "bitcoin": {
        "name": "加密货币",
        "svg": '<circle cx="12" cy="12" r="10"/><path d="M9.5 7.5h5a2 2 0 0 1 0 4h-5"/><path d="M9.5 11.5h5.5a2 2 0 0 1 0 4h-5.5"/><line x1="12" y1="3" x2="12" y2="7"/><line x1="12" y1="16" x2="12" y2="21"/>',
        "keywords": ["加密货币", "比特币", "区块链", "defi"]
    },
    
    # 游戏开发
    "gamepad": {
        "name": "游戏",
        "svg": '<path d="M6 11h4M8 9v4M15 12h.01M18 10h.01"/><rect x="2" y="6" width="20" height="12" rx="2"/>',
        "keywords": ["游戏", "游戏开发", "unity", "虚幻引擎", "game"]
    },
    "box_3d": {
        "name": "3D建模",
        "svg": '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
        "keywords": ["3d", "建模", "图形", "opengl", "webgl", "three.js"]
    },
    
    # 设计
    "palette": {
        "name": "设计",
        "svg": '<circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>',
        "keywords": ["设计", "ui", "ux", "界面", "视觉", "配色"]
    },
    "image": {
        "name": "图像",
        "svg": '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
        "keywords": ["图像", "图片", "ps", "设计", "opencv"]
    },
    "video": {
        "name": "视频",
        "svg": '<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>',
        "keywords": ["视频", "多媒体", "音视频", "ffmpeg", "直播"]
    },
    
    # 通用概念
    "rocket": {
        "name": "火箭",
        "svg": '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
        "keywords": ["快速", "入门", "实战", "项目", "启动"]
    },
    "target": {
        "name": "目标",
        "svg": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
        "keywords": ["目标", "重点", "核心", "关键"]
    },
    "puzzle": {
        "name": "拼图",
        "svg": '<path d="M4 14a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path d="M4 8V6a2 2 0 0 1 2-2h3"/><path d="M15 4h3a2 2 0 0 1 2 2v2"/><circle cx="12" cy="9" r="2"/>',
        "keywords": ["综合", "整合", "全栈", "完整"]
    },
    "layers": {
        "name": "层次",
        "svg": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
        "keywords": ["架构", "分层", "设计模式", "层次"]
    },
    "compass": {
        "name": "指南针",
        "svg": '<circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>',
        "keywords": ["导航", "指南", "入门", "roadmap", "学习路线"]
    },
    "award": {
        "name": "奖励",
        "svg": '<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89L17 22l-5-3-5 3 1.523-9.11"/>',
        "keywords": ["成就", "认证", "证书", "奖励", "完成"]
    },
    "star": {
        "name": "星星",
        "svg": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
        "keywords": ["精选", "推荐", "热门", "优质", "收藏"]
    },
    "trending": {
        "name": "趋势",
        "svg": '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
        "keywords": ["趋势", "热门", "流行", "前沿", "最新"]
    },
    "zap": {
        "name": "闪电",
        "svg": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
        "keywords": ["快速", "高效", "性能", "优化", "闪电"]
    },
    "shield": {
        "name": "安全盾",
        "svg": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
        "keywords": ["安全", "防护", "保护", "安全性", "权限"]
    },
    "key": {
        "name": "密钥",
        "svg": '<path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>',
        "keywords": ["密钥", "认证", "token", "jwt", "登录"]
    },
    
    # 软件工程基础
    "file_code": {
        "name": "代码文件",
        "svg": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><polyline points="10 13 8 15 10 17"/><polyline points="14 13 16 15 14 17"/>',
        "keywords": ["源代码", "编程", "代码文件", "软件开发"]
    },
    "folder": {
        "name": "项目",
        "svg": '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
        "keywords": ["项目", "工程", "文件夹", "项目管理"]
    },
    "package": {
        "name": "打包",
        "svg": '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
        "keywords": ["打包", "部署", "发布", "构建", "package"]
    },
    
    # 需求与设计
    "clipboard": {
        "name": "需求",
        "svg": '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>',
        "keywords": ["需求", "需求分析", "软件需求", "需求工程", "文档"]
    },
    "layout": {
        "name": "架构设计",
        "svg": '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/>',
        "keywords": ["架构", "系统设计", "软件架构", "设计", "uml"]
    },
    "git_branch": {
        "name": "版本分支",
        "svg": '<line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>',
        "keywords": ["分支", "版本管理", "git分支", "协作开发"]
    },
    "git_merge": {
        "name": "代码合并",
        "svg": '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M6 21V9a9 9 0 0 0 9 9"/>',
        "keywords": ["合并", "代码合并", "merge", "集成"]
    },
    "git_pull": {
        "name": "拉取请求",
        "svg": '<circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><line x1="6" y1="9" x2="6" y2="21"/>',
        "keywords": ["pr", "pull request", "代码审查", "review"]
    },
    
    # 编译原理与系统
    "cpu_chip": {
        "name": "编译",
        "svg": '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v2M15 2v2M9 20v2M15 20v2M20 9h2M20 14h2M2 9h2M2 14h2"/>',
        "keywords": ["编译", "编译原理", "编译器", "语法分析", "词法分析"]
    },
    "monitor": {
        "name": "操作系统",
        "svg": '<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>',
        "keywords": ["操作系统", "os", "linux", "windows", "进程", "线程"]
    },
    "hard_drive": {
        "name": "存储",
        "svg": '<line x1="22" y1="12" x2="2" y2="12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><line x1="6" y1="16" x2="6.01" y2="16"/><line x1="10" y1="16" x2="10.01" y2="16"/>',
        "keywords": ["存储", "磁盘", "文件系统", "io", "存储系统"]
    },
    "memory": {
        "name": "内存",
        "svg": '<rect x="2" y="7" width="20" height="10" rx="2"/><line x1="6" y1="11" x2="6" y2="13"/><line x1="10" y1="11" x2="10" y2="13"/><line x1="14" y1="11" x2="14" y2="13"/><line x1="18" y1="11" x2="18" y2="13"/>',
        "keywords": ["内存", "ram", "内存管理", "缓存", "cache"]
    },
    
    # 计算机网络
    "globe": {
        "name": "互联网",
        "svg": '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
        "keywords": ["互联网", "网络", "internet", "www", "全球网"]
    },
    "route": {
        "name": "路由",
        "svg": '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/><circle cx="18" cy="5" r="3"/>',
        "keywords": ["路由", "网络路由", "router", "tcp/ip", "网络协议"]
    },
    "antenna": {
        "name": "通信",
        "svg": '<path d="M2 12h2M20 12h2M6.34 7.34l-1.41-1.41M19.07 4.93l-1.41 1.41M6.34 16.66l-1.41 1.41M19.07 19.07l-1.41-1.41M12 2v2M12 20v2"/><circle cx="12" cy="12" r="3"/>',
        "keywords": ["通信", "信号", "网络通信", "无线"]
    },
    
    # 数据库系统
    "database_backup": {
        "name": "数据库备份",
        "svg": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3"/><path d="M21 5v6"/><path d="M16 19h6M19 16v6"/>',
        "keywords": ["备份", "恢复", "数据备份", "灾备"]
    },
    "table": {
        "name": "数据表",
        "svg": '<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/>',
        "keywords": ["表", "数据表", "关系型", "表设计"]
    },
    "index": {
        "name": "索引",
        "svg": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/><line x1="10" y1="8" x2="16" y2="8"/><line x1="10" y1="12" x2="16" y2="12"/><line x1="10" y1="16" x2="16" y2="16"/>',
        "keywords": ["索引", "数据库索引", "btree", "查询优化"]
    },
    
    # 软件测试
    "check_circle": {
        "name": "验证",
        "svg": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
        "keywords": ["验证", "测试通过", "校验", "正确性"]
    },
    "x_circle": {
        "name": "错误",
        "svg": '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
        "keywords": ["错误", "失败", "异常", "bug"]
    },
    "alert": {
        "name": "警告",
        "svg": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
        "keywords": ["警告", "warning", "注意", "风险"]
    },
    "search": {
        "name": "搜索",
        "svg": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>',
        "keywords": ["搜索", "查询", "检索", "search"]
    },
    
    # 性能与优化
    "activity": {
        "name": "性能",
        "svg": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
        "keywords": ["性能", "监控", "性能优化", "指标", "metrics"]
    },
    "gauge": {
        "name": "指标",
        "svg": '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
        "keywords": ["指标", "仪表盘", "监控", "dashboard"]
    },
    "timer": {
        "name": "时间",
        "svg": '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2 2"/><path d="M5 3L2 6M22 6l-3-3M6 19l-2 2M18 19l2 2"/>',
        "keywords": ["时间", "定时", "延迟", "性能", "响应时间"]
    },
    "speedometer": {
        "name": "速度",
        "svg": '<path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/><circle cx="12" cy="12" r="3"/>',
        "keywords": ["速度", "性能", "快速", "加速", "优化"]
    },
    
    # 安全
    "fingerprint": {
        "name": "生物识别",
        "svg": '<path d="M2 12C2 6.5 6.5 2 12 2a10 10 0 0 1 8 4"/><path d="M5 19.5C5.5 18 6 15 6 12c0-.7.12-1.37.34-2"/><path d="M17.29 21.02c.12-.6.43-2.3.5-3.02"/><path d="M12 10a2 2 0 0 0-2 2c0 1.02-.1 2.51-.26 4"/><path d="M8.65 22c.21-.66.45-1.32.57-2"/><path d="M14 13.12c0 2.38 0 6.38-1 8.88"/><path d="M2 16h.01M21.8 16c.2-2 .131-5.354 0-6"/><path d="M9 6.8a6 6 0 0 1 9 5.2c0 .47 0 1.17-.02 2"/>',
        "keywords": ["生物识别", "指纹", "认证", "身份验证"]
    },
    "lock_open": {
        "name": "解锁",
        "svg": '<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/>',
        "keywords": ["解锁", "权限", "授权", "访问控制"]
    },
    "eye": {
        "name": "可见性",
        "svg": '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
        "keywords": ["可见性", "查看", "监控", "观察"]
    },
    "eye_off": {
        "name": "隐藏",
        "svg": '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>',
        "keywords": ["隐藏", "隐私", "加密", "保密"]
    },
    
    # 团队协作
    "users": {
        "name": "团队",
        "svg": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
        "keywords": ["团队", "协作", "用户", "成员", "团队协作"]
    },
    "user_check": {
        "name": "用户验证",
        "svg": '<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><polyline points="17 11 19 13 23 9"/>',
        "keywords": ["用户验证", "权限", "审核", "认证"]
    },
    "share": {
        "name": "分享",
        "svg": '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>',
        "keywords": ["分享", "共享", "协作", "社交"]
    },
    
    # 文档
    "file_text": {
        "name": "文档",
        "svg": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
        "keywords": ["文档", "说明", "readme", "文档编写", "技术文档"]
    },
    "pencil": {
        "name": "编辑",
        "svg": '<path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/>',
        "keywords": ["编辑", "修改", "写作", "编写"]
    },
    "list": {
        "name": "列表",
        "svg": '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
        "keywords": ["列表", "清单", "目录", "索引"]
    },
    
    # 其他重要概念
    "refresh": {
        "name": "刷新",
        "svg": '<path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>',
        "keywords": ["刷新", "重载", "更新", "reload", "同步"]
    },
    "download": {
        "name": "下载",
        "svg": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
        "keywords": ["下载", "导出", "保存", "下载文件"]
    },
    "upload": {
        "name": "上传",
        "svg": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
        "keywords": ["上传", "导入", "发布", "上传文件"]
    },
    "play": {
        "name": "运行",
        "svg": '<polygon points="5 3 19 12 5 21 5 3"/>',
        "keywords": ["运行", "执行", "启动", "play", "开始"]
    },
    "pause": {
        "name": "暂停",
        "svg": '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>',
        "keywords": ["暂停", "停止", "pause", "中断"]
    },
    "link": {
        "name": "链接",
        "svg": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
        "keywords": ["链接", "关联", "连接", "url", "超链接"]
    },
}

# 系统提示词
PLAN_ICON_SYSTEM_PROMPT = """你是一个学习计划图标选择专家。根据用户的学习计划名称和相关资源主题，从预定义的图标库中选择最合适的图标。

## 你的任务
1. 分析学习计划的主题和内容
2. 从图标库中选择 **1个** 最契合的图标

## 图标库
以下是可用的图标及其适用场景：

{icon_descriptions}

## 输出要求
严格按以下 JSON 格式输出，不要输出任何其他内容：
{{
  "icon_key": "选择的图标key",
  "description": "图标含义的简短描述（10字以内）"
}}

## 示例
如果计划是"Python数据分析"，应该选择：
{{"icon_key": "python", "description": "Python编程"}}

如果计划是"深度学习入门"，应该选择：
{{"icon_key": "brain", "description": "AI大脑学习"}}
"""


def get_icon_descriptions() -> str:
    """生成图标库的描述文本"""
    lines = []
    for key, icon in ICON_LIBRARY.items():
        keywords_str = "、".join(icon["keywords"][:5])
        lines.append(f"- **{key}**（{icon['name']}）：适用于 {keywords_str} 等主题")
    return "\n".join(lines)


def get_icon_svg(icon_key: str) -> str:
    """
    根据选择的图标 key 生成最终的 SVG
    
    Args:
        icon_key: 图标 key，如 "code"
    
    Returns:
        完整的 SVG 字符串
    """
    if not icon_key or icon_key not in ICON_LIBRARY:
        icon_key = "book"
    
    icon = ICON_LIBRARY[icon_key]
    return f'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{icon["svg"]}</svg>'


def get_system_prompt() -> str:
    """获取完整的系统提示词"""
    return PLAN_ICON_SYSTEM_PROMPT.format(icon_descriptions=get_icon_descriptions())
