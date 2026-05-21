from __future__ import annotations

from pathlib import Path

from invesagent_core.config.settings import settings

def get_project_root() -> Path:
    """Return project root path."""
    return settings.project_root


def get_data_cache_dir() -> Path:
    """Return data cache directory and ensure it exists."""
    path = get_project_root() / settings.data_cache_dir
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_charts_dir() -> Path:
    """Return charts directory and ensure it exists."""
    path = get_project_root() / settings.charts_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_reports_dir() -> Path:
    """Return reports directory and ensure it exists."""
    path = get_project_root() / settings.reports_dir
    path.mkdir(parents=True, exist_ok=True)
    return path