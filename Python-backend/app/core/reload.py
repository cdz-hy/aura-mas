from pathlib import Path


def get_reload_dirs(project_root: Path) -> list[str]:
    return [str((project_root / "app").resolve())]
