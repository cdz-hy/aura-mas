"""
通用 Skill Loader — 按约定目录结构从 skills/ 加载任意 skill 文件

约定结构:
    skills/<skill-name>/
    ├── SKILL.md              # 必须
    ├── references/           # 可选, *.md
    ├── styles/               # 可选, *.md
    └── assets/templates/     # 可选, *.html
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("skills.loader")

# skills 目录位于 Python-backend/skills/
SKILLS_ROOT = Path(__file__).resolve().parent.parent.parent / "skills"


@dataclass
class SkillBundle:
    """一个 skill 的全部文件内容"""
    name: str
    skill_md: str = ""                          # SKILL.md 原文
    references: dict[str, str] = field(default_factory=dict)  # {stem: content}
    styles: dict[str, str] = field(default_factory=dict)      # {stem: content}
    templates: dict[str, str] = field(default_factory=dict)   # {stem: content}


def _read_files_in_dir(dir_path: Path, suffix: str) -> dict[str, str]:
    """读取目录下指定后缀的文件，返回 {stem: content}"""
    result = {}
    if not dir_path.is_dir():
        return result
    for f in sorted(dir_path.iterdir()):
        if f.is_file() and f.suffix == suffix:
            try:
                result[f.stem] = f.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"读取文件失败 {f}: {e}")
    return result


def load_skill(skill_name: str) -> SkillBundle:
    """
    从 skills/<skill_name>/ 加载所有文件。

    Args:
        skill_name: skill 目录名，例如 "jacky-motion-main"

    Returns:
        SkillBundle 包含所有加载的文件内容

    Raises:
        FileNotFoundError: skill 目录不存在或缺少 SKILL.md
    """
    skill_dir = SKILLS_ROOT / skill_name

    if not skill_dir.is_dir():
        raise FileNotFoundError(f"Skill 目录不存在: {skill_dir}")

    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.is_file():
        raise FileNotFoundError(f"SKILL.md 不存在: {skill_md_path}")

    skill_md = skill_md_path.read_text(encoding="utf-8")

    references = _read_files_in_dir(skill_dir / "references", ".md")
    styles = _read_files_in_dir(skill_dir / "styles", ".md")
    templates = _read_files_in_dir(skill_dir / "assets" / "templates", ".html")

    bundle = SkillBundle(
        name=skill_name,
        skill_md=skill_md,
        references=references,
        styles=styles,
        templates=templates,
    )

    logger.info(
        f"已加载 skill '{skill_name}': "
        f"SKILL.md={len(skill_md)}字符, "
        f"references={len(references)}, "
        f"styles={len(styles)}, "
        f"templates={len(templates)}"
    )

    return bundle
