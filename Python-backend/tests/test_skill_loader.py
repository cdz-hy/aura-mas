"""Skill Loader 单元测试"""
import pytest
from pathlib import Path
from app.skills.loader import load_skill, SkillBundle, SKILLS_ROOT


class TestLoadSkill:
    """测试 load_skill 函数"""

    def test_load_jacky_motion_main(self):
        """加载真实的 jacky-motion-main skill"""
        bundle = load_skill("jacky-motion-main")

        assert isinstance(bundle, SkillBundle)
        assert bundle.name == "jacky-motion-main"

        # SKILL.md 必须存在且非空
        assert len(bundle.skill_md) > 0
        assert "Aura 教学动画导演" in bundle.skill_md

        # references 应包含 quality-check
        assert "quality-check" in bundle.references
        assert "验收检查" in bundle.references["quality-check"]

        # templates 应包含 4 个 style HTML
        assert len(bundle.templates) == 4
        assert "apple-tech-gradient" in bundle.templates
        assert "editorial-magazine" in bundle.templates
        assert "finance-studio-cards" in bundle.templates
        assert "newspaper-evidence" in bundle.templates

        # styles 应包含 4 个 style md
        assert len(bundle.styles) == 4

    def test_nonexistent_skill_raises(self):
        """不存在的 skill 目录应抛出 FileNotFoundError"""
        with pytest.raises(FileNotFoundError, match="Skill 目录不存在"):
            load_skill("nonexistent-skill")

    def test_skills_root_exists(self):
        """SKILLS_ROOT 指向的目录必须存在"""
        assert SKILLS_ROOT.is_dir()
