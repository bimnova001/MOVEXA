"""Project Manager (architecture doc 5).

Responsibilities:
- create project directories and ``project.json``
- load projects preserving unknown fields (lossless round trip)
- save projects with atomic write (temp file + os.replace)
- track recently opened projects for the dashboard
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from project.schema import ProjectSettings, SCHEMA_VERSION, Project, validate_project

log = logging.getLogger(__name__)

PROJECT_FILE = "project.json"
_DIR_CHANNELS = ("assets", "scenes", "cache", "exports")

ASSET_SUBDIRS = {
    "characters": "assets/characters",
    "backgrounds": "assets/backgrounds",
    "props": "assets/props",
    "audio": "assets/audio",
    "other": "assets/other",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ProjectManager:
    def __init__(self) -> None:
        self.current: Project | None = None
        self.current_dir: Path | None = None

    def create_project(
        self,
        directory: Path | str,
        name: str,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
    ) -> Project:
        """Create a fresh project at *directory*.

        Refuses to overwrite an existing project.json (FileExistsError).
        """
        directory = Path(directory)
        project_file = directory / PROJECT_FILE
        if project_file.exists():
            raise FileExistsError(f"project already exists: {project_file}")

        directory.mkdir(parents=True, exist_ok=True)
        for sub in _DIR_CHANNELS:
            (directory / sub).mkdir(exist_ok=True)
        for sub in ASSET_SUBDIRS.values():
            Path(directory, *sub.split("/")).mkdir(exist_ok=True)

        project = Project(
            project_id=f"project_{uuid.uuid4().hex[:8]}",
            name=name,
            schema_version=SCHEMA_VERSION,
            created_at=_utc_now(),
            modified_at=_utc_now(),
        )
        project.settings = ProjectSettings(width=width, height=height, fps=fps)

        self._write(project_file, project.to_data())
        self.current = project
        self.current_dir = directory
        self.add_recent(directory)
        log.info("created project %s at %s", project.project_id, directory)
        return project

    def open_project(self, directory: Path | str) -> Project:
        directory = Path(directory)
        project_file = directory / PROJECT_FILE
        if not project_file.is_file():
            raise FileNotFoundError(f"not a MOVEXA project: {project_file}")

        with open(project_file, encoding="utf-8") as fh:
            data: dict[str, Any] = json.load(fh)

        project = Project.from_data(data)
        if project.schema_version != SCHEMA_VERSION:
            # Loader keeps data; validation will flag problems to the caller.
            log.warning("schema version %s loaded (expected %s)",
                        project.schema_version, SCHEMA_VERSION)

        problems = validate_project(project)
        for problem in problems:
            log.warning("project validation: %s", problem)

        self.current = project
        self.current_dir = directory
        self.add_recent(directory)
        return project

    def save(self) -> Project:
        if self.current is None or self.current_dir is None:
            raise RuntimeError("no project open")
        self.current.modified_at = _utc_now()
        self._write(self.current_dir / PROJECT_FILE, self.current.to_data())
        return self.current

    @staticmethod
    def _write(project_file: Path, data: dict[str, Any]) -> None:
        tmp = project_file.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, project_file)

    def asset_subdir(self, category: str) -> Path:
        if self.current_dir is None:
            raise RuntimeError("no project open")
        sub = ASSET_SUBDIRS.get(category, ASSET_SUBDIRS["other"])
        return Path(self.current_dir, *sub.split("/"))

    def recent_file(self) -> Path:
        base = Path(os.environ.get("APPDATA", Path.home())) / "MOVEXA"
        base.mkdir(parents=True, exist_ok=True)
        return base / "recent_projects.json"

    def add_recent(self, directory: Path | str) -> list[str]:
        directory = str(Path(directory).resolve())
        recents = self.load_recent()
        recents = [directory] + [d for d in recents if d != directory]
        recents = recents[:10]
        with open(self.recent_file(), "w", encoding="utf-8") as fh:
            json.dump(recents, fh)
        return recents

    def remove_recent(self, directory: Path | str) -> list[str]:
        """Drop one entry from recents (the project folder itself stays)."""
        directory = str(Path(directory).resolve())
        recents = [d for d in self.load_recent() if d != directory]
        with open(self.recent_file(), "w", encoding="utf-8") as fh:
            json.dump(recents, fh)
        return recents

    def load_recent(self) -> list[str]:
        try:
            with open(self.recent_file(), encoding="utf-8") as fh:
                recents = json.load(fh)
        except (OSError, ValueError):
            return []
        if not isinstance(recents, list) or not all(isinstance(r, str) for r in recents):
            return []
        return [r for r in recents if (Path(r) / PROJECT_FILE).is_file()]
