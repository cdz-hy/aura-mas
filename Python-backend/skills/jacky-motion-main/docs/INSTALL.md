# 安装与更新

Jacky Motion 是一个标准 skill 仓库：根目录包含 `SKILL.md`。安装方式由你的宿主 agent 决定。

## 最简安装：skills installer

如果你的环境支持 `skills` installer，先使用最短命令：

```bash
npx skills add https://github.com/Jackywxsz/jacky-motion
```

在需要指定 agent、全局安装或非交互安装时，再追加对应参数。例如 Codex 环境：

```bash
npx skills add https://github.com/Jackywxsz/jacky-motion --skill jacky-motion -a codex -g -y
```

## 手动安装：克隆到宿主 skills 目录

不同工具读取 skills 的目录不同。通用格式是：

```bash
git clone https://github.com/Jackywxsz/jacky-motion.git <your-skills-dir>/jacky-motion
```

例如使用 CC Switch 时：

```bash
mkdir -p ~/.cc-switch/skills
git clone https://github.com/Jackywxsz/jacky-motion.git ~/.cc-switch/skills/jacky-motion
```

## 更新

进入你安装的目录后拉取最新版本：

```bash
cd <your-skills-dir>/jacky-motion
git pull
```

## 调用方式

调用符号由宿主环境决定，不要把某一种前缀当成通用规则：

```text
Claude Code / CC Switch 等环境可能是：/jacky-motion
Codex 或其他 skills 环境可能是：$jacky-motion
有些环境会根据 skill 名称或描述自动匹配。
```

如果不确定，优先查看当前 agent 的 skills 列表、slash commands 列表或插件面板。

## 卸载

删除你安装的目录即可：

```bash
rm -rf <your-skills-dir>/jacky-motion
```
