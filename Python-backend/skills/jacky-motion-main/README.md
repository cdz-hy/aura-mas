# Jacky Motion

Jacky Motion 是一个中文口播稿转 16:9 信息动画 HTML 的 agent skill。它面向知识博主、课程创作者、AI 工具讲解、商业分析和观点型短视频，把一篇口播稿拆成可录屏的动态网页演示。

它不是通用 PPT 模板，也不是只负责“做得好看”的视觉包装。核心目标是：让信息层次更清楚，让动画节奏服务口播表达。

## 核心能力

- 将中文口播稿拆成镜头节拍，并检查信息密度、逻辑断点和屏幕文字长度。
- 按固定流程完成：审稿、分镜、锁风格、生成 HTML、验收、配音录制。
- 输出单文件 16:9 HTML，适合浏览器打开、手动点击推进、全屏录屏。
- 内置 4 种视觉风格：苹果科技渐变、杂志信息图、财经演播室卡片、报纸剪贴纪实。
- 支持后续接入 TTS 音频控制，让 HTML 进入自动播放录屏模式。

## 安装

最简方式取决于你的宿主 agent。这个仓库只提供标准 skill 文件，具体安装到哪里、怎么唤起，由 Claude Code、Codex、CC Switch、Cursor 等宿主环境决定。

### 通用安装器

如果你的环境支持 `skills` installer，最短命令是：

```bash
npx skills add https://github.com/Jackywxsz/jacky-motion
```

需要非交互或指定 agent 时，再按你的环境追加参数。例如 Codex 环境可以使用：

```bash
npx skills add https://github.com/Jackywxsz/jacky-motion --skill jacky-motion -a codex -g -y
```

### 手动安装

如果你的 agent 读取某个本地 skills 目录，把仓库克隆到对应目录即可。下面只是常见例子，不代表所有环境都必须使用 CC Switch：

```bash
git clone https://github.com/Jackywxsz/jacky-motion.git <your-skills-dir>/jacky-motion
```

使用 CC Switch 时通常是：

```bash
mkdir -p ~/.cc-switch/skills
git clone https://github.com/Jackywxsz/jacky-motion.git ~/.cc-switch/skills/jacky-motion
```

## 使用

在支持 skill 的 agent 中调用。注意：调用符号不是这个仓库决定的，而是宿主环境决定的。

```text
Claude Code / CC Switch 等环境可能是：/jacky-motion
Codex 或其他 skills 环境可能是：$jacky-motion
有些环境会根据 skill 名称或描述自动匹配，不需要手动输入前缀。
```

然后贴入口播稿，并说明你想要的方向，例如：

```text
用这篇口播稿生成可录屏的 16:9 信息动画 HTML，风格偏杂志信息图，先走完整流程。
```

推荐工作方式：

1. 先让 skill 审稿，判断脚本是通过、轻改还是需要重写。
2. 确认分镜，每个节拍都要有一句核心信息、一个视觉动词和短屏幕文字。
3. 确认风格，整条视频只使用一种主风格。
4. 生成 HTML 后做验收，重点看截图是否完整、文字是否溢出、录屏安全区是否够。
5. 验收通过后再决定自行配音，或走 TTS 自动播放录屏。

## 设计理念

Jacky Motion 的底层理念是“信息表达驱动一切”。

- 布局服务信息层次，不用装饰性卡片堆满画面。
- 动画服务口播节奏，不为了炫技而动。
- 先把脚本讲清楚，再考虑画面怎么高级。
- 每个镜头必须有视觉动词，例如高亮、连接、增长、对比、推近、展开、流动、堆叠。
- 每个节拍用 4 段式编排：主视觉入场、画面重构、关键词强调、标注落位。

更多说明见 [docs/DESIGN.md](docs/DESIGN.md)。

## 内置风格

| 风格 ID | 中文名 | 适合内容 | 气质 |
|---|---|---|---|
| `apple-tech-gradient` | 苹果科技渐变演示风 | AI 工具、产品概念、抽象机制、未来科技 | 克制 keynote，空间层级清楚 |
| `editorial-magazine` | 杂志信息图风 | 深度知识、方法论、研究解读、人物故事 | 高级编辑版面，像杂志特稿 |
| `finance-studio-cards` | 财经演播室卡片风 | 商业分析、公司分析、产业结构、宏观政策 | 专业信息大屏，强调关系和数据 |
| `newspaper-evidence` | 报纸剪贴纪实风 | 新闻事件、历史、政策、社会议题、案件调查 | 证据、档案、纪录片 |

详细风格规则见 [docs/STYLES.md](docs/STYLES.md)。

## 仓库结构

```text
.
├── SKILL.md                  # skill 主入口
├── agents/openai.yaml         # agent 展示信息
├── assets/templates/          # 4 种风格的 HTML 模板
├── styles/                    # 4 种风格的文字规则
├── references/                # 审稿和验收标准
├── docs/                      # 安装、设计、流程说明
├── README.md
├── LICENSE
└── .gitignore
```

## 输出物

默认输出是一个可录屏的 HTML 文件，而不是直接渲染 MP4。这样更适合内容创作者快速调整文案、截图和节奏。

如果需要视频，可以在 HTML 验收通过后，用浏览器全屏打开，再用 QuickTime、OBS 或系统录屏工具录制。需要自动播完时，可以进入 TTS 流程，给每个 step 注入音频并启用自动播放模式。

## 文档

- [安装与更新](docs/INSTALL.md)
- [设计理念](docs/DESIGN.md)
- [6 阶段工作流](docs/WORKFLOW.md)
- [内置风格说明](docs/STYLES.md)

## License

MIT
