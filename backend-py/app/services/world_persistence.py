"""Bridge legacy world JSON files to the SaaS world repository."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.repositories import WorldRepository


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)


class WorldPersistenceService:
    """Hydrate before legacy layer construction and sync after mutations."""

    def __init__(self, repository: WorldRepository, *, tenant_id: str, companion_id: str = "xiaoman") -> None:
        self.repository = repository
        self.tenant_id = tenant_id
        self.companion_id = companion_id

    def hydrate(self, *, user_id: str, user_data_dir: str) -> int:
        restored = 0
        root = Path(user_data_dir)
        for side in ("user", "xiaoman"):
            for layer in self._known_layers(root / side):
                data = self.repository.load_layer(self.tenant_id, user_id, self.companion_id, side, layer)
                if data:
                    _write_json(root / side / f"{layer}.json", data)
                    restored += 1
        return restored

    def sync(self, *, user_id: str, user_data_dir: str) -> int:
        saved = 0
        root = Path(user_data_dir)
        for side in ("user", "xiaoman"):
            for path in sorted((root / side).glob("*.json")):
                with path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, dict):
                    self.repository.save_layer(
                        self.tenant_id,
                        user_id,
                        self.companion_id,
                        side,
                        path.stem,
                        data,
                    )
                    saved += 1
        return saved

    @staticmethod
    def _known_layers(side_dir: Path) -> set[str]:
        layers = {path.stem for path in side_dir.glob("*.json")}
        layers.update(
            {
                "identity",
                "living_env",
                "schedule",
                "social_graph",
                "emotions",
                "skills",
            }
        )
        if side_dir.name == "user":
            layers.update({"profile", "mid_term_memory", "long_term_memory"})
        else:
            layers.add("user_understanding")
        return layers
