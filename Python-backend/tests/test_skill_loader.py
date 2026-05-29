"""Skill Loader 单元测试"""
import pytest
from app.skills.loader import load_skill, SkillBundle, SKILLS_ROOT


class TestLoadSkillWithTmpPath:
    """使用 tmp_path 的单元测试 — 不依赖真实 skill 文件"""

    def test_loads_skill_md_and_optional_dirs(self, tmp_path, monkeypatch):
        """加载包含 SKILL.md + references + styles + templates 的 skill"""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")

        ref_dir = skill_dir / "references"
        ref_dir.mkdir()
        (ref_dir / "guide.md").write_text("guide content", encoding="utf-8")

        style_dir = skill_dir / "styles"
        style_dir.mkdir()
        (style_dir / "dark.md").write_text("dark style", encoding="utf-8")

        tpl_dir = skill_dir / "assets" / "templates"
        tpl_dir.mkdir(parents=True)
        (tpl_dir / "tpl.html").write_text("<html></html>", encoding="utf-8")

        monkeypatch.setattr("app.skills.loader.SKILLS_ROOT", tmp_path)
        bundle = load_skill("test-skill")

        assert isinstance(bundle, SkillBundle)
        assert bundle.name == "test-skill"
        assert bundle.skill_md == "# Test Skill"
        assert bundle.references == {"guide": "guide content"}
        assert bundle.styles == {"dark": "dark style"}
        assert bundle.templates == {"tpl": "<html></html>"}

    def test_missing_directory_raises(self):
        """不存在的 skill 目录应抛出 FileNotFoundError"""
        with pytest.raises(FileNotFoundError, match="Skill 目录不存在"):
            load_skill("nonexistent-skill")

    def test_missing_skill_md_raises(self, tmp_path, monkeypatch):
        """目录存在但缺少 SKILL.md 应抛出 FileNotFoundError"""
        skill_dir = tmp_path / "no-md-skill"
        skill_dir.mkdir()

        monkeypatch.setattr("app.skills.loader.SKILLS_ROOT", tmp_path)
        with pytest.raises(FileNotFoundError, match="SKILL.md 不存在"):
            load_skill("no-md-skill")

    def test_empty_optional_dirs(self, tmp_path, monkeypatch):
        """只有 SKILL.md，没有 references/styles/templates 也能正常加载"""
        skill_dir = tmp_path / "minimal-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("minimal", encoding="utf-8")

        monkeypatch.setattr("app.skills.loader.SKILLS_ROOT", tmp_path)
        bundle = load_skill("minimal-skill")

        assert bundle.skill_md == "minimal"
        assert bundle.references == {}
        assert bundle.styles == {}
        assert bundle.templates == {}


class TestLoadRealSkill:
    """加载真实 jacky-motion-main 的集成冒烟测试"""

    def test_load_jacky_motion_main(self):
        bundle = load_skill("jacky-motion-main")

        assert bundle.name == "jacky-motion-main"
        assert len(bundle.skill_md) > 0
        assert "quality-check" in bundle.references
        assert len(bundle.templates) == 4
        assert len(bundle.styles) == 4

    def test_skills_root_exists(self):
        assert SKILLS_ROOT.is_dir()
