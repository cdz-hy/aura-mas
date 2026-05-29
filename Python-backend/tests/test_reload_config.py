from app.core.reload import get_reload_dirs


def test_reload_dirs_only_include_app_source_dir(tmp_path):
    project_root = tmp_path / "backend"
    app_dir = project_root / "app"
    temp_dir = project_root / "temp-folder"

    app_dir.mkdir(parents=True)
    temp_dir.mkdir()

    assert get_reload_dirs(project_root) == [str(app_dir.resolve())]
