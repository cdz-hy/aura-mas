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
import time
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


# ── Skill 缓存 ──
# key: skill_name, value: (mtime_of_SKILL_MD, SkillBundle)
_skill_cache: dict[str, tuple[float, SkillBundle]] = {}


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


def _get_skill_mtime(skill_dir: Path) -> float:
    """获取 skill 目录下所有文件的最大 mtime，确保任意文件变化都能刷新缓存"""
    max_mtime = 0.0
    for f in skill_dir.rglob("*"):
        if f.is_file():
            try:
                mtime = f.stat().st_mtime
                if mtime > max_mtime:
                    max_mtime = mtime
            except OSError:
                pass
    return max_mtime


def load_skill(skill_name: str) -> SkillBundle:
    """
    从 skills/<skill_name>/ 加载所有文件。
    支持 mtime 缓存：如果 skill 目录下任意文件的 mtime 未变则返回缓存。

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

    # 检查缓存：如果 skill 目录下所有文件的 mtime 未变，返回缓存
    current_mtime = _get_skill_mtime(skill_dir)
    cached = _skill_cache.get(skill_name)
    if cached is not None:
        cached_mtime, cached_bundle = cached
        if cached_mtime == current_mtime:
            logger.debug(f"命中缓存: skill '{skill_name}' (mtime={current_mtime})")
            return cached_bundle

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

    # 更新缓存
    _skill_cache[skill_name] = (current_mtime, bundle)

    logger.info(
        f"已加载 skill '{skill_name}': "
        f"SKILL.md={len(skill_md)}字符, "
        f"references={len(references)}, "
        f"styles={len(styles)}, "
        f"templates={len(templates)}"
    )

    return bundle
