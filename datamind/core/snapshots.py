"""Profile-scoped surface manifests and published snapshots.

The store is intentionally small and file backed. It provides the lifecycle
semantics used by the research branch: immutable snapshot records, an atomic
current pointer, and revision metadata attached to request evidence. Physical
providers can stage their own artifacts before publication.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

from .contracts import DataSurface


class SurfaceManifest(BaseModel):
    """Stable contract advertised for one materialized surface."""

    model_config = ConfigDict(populate_by_name=True)

    surface: DataSurface
    operations: list[str] = Field(default_factory=list)
    schema_: dict[str, Any] = Field(default_factory=dict, alias="schema")
    sources: list[str] = Field(default_factory=list)
    revision: int = 0
    evidence_type: str = "source-linked"
    freshness: str = "unknown"
    estimated_cost: float | None = None
    fingerprint: str | None = None


class ProfileSnapshot(BaseModel):
    """Immutable set of surface revisions visible to a profile."""

    snapshot_id: str
    profile: str
    parent_id: str | None = None
    revisions: dict[str, int] = Field(default_factory=dict)
    manifests: dict[str, SurfaceManifest] = Field(default_factory=dict)
    status: str = "published"
    created_at: float = Field(default_factory=time.time)


class SnapshotStore:
    """Atomic JSON-backed snapshot catalog for one profile."""

    def __init__(self, *, storage_dir: Path, profile: str) -> None:
        self.storage_dir = Path(storage_dir)
        self.profile = profile
        self.root = self.storage_dir / "snapshots"
        self.root.mkdir(parents=True, exist_ok=True)
        self._current_path = self.root / "current.json"
        self._counter_path = self.root / "counter.json"
        self._lock = asyncio.Lock()

    @staticmethod
    def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)

    def _read_snapshot(self, snapshot_id: str) -> ProfileSnapshot:
        path = self.root / f"{snapshot_id}.json"
        if not path.is_file():
            raise FileNotFoundError(f"unknown snapshot: {snapshot_id}")
        return ProfileSnapshot.model_validate(json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def _key(value: DataSurface | str) -> str:
        return value.value if isinstance(value, DataSurface) else str(value)

    @property
    def current_id(self) -> str | None:
        if not self._current_path.is_file():
            return None
        try:
            return str(json.loads(self._current_path.read_text(encoding="utf-8"))["snapshot_id"])
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            return None

    def current(self) -> ProfileSnapshot | None:
        snapshot_id = self.current_id
        return self._read_snapshot(snapshot_id) if snapshot_id else None

    def get(self, snapshot_id: str) -> ProfileSnapshot:
        return self._read_snapshot(snapshot_id)

    async def ensure_initial(
        self, manifests: Mapping[DataSurface | str, SurfaceManifest]
    ) -> ProfileSnapshot:
        existing = self.current()
        if existing is not None:
            return existing
        return await self.publish(manifests, parent_id=None)

    async def publish(
        self,
        manifests: Mapping[DataSurface | str, SurfaceManifest],
        *,
        parent_id: str | None = None,
    ) -> ProfileSnapshot:
        """Write an immutable snapshot and atomically advance current.json."""
        async with self._lock:
            parent = parent_id or self.current_id
            counter = 0
            if self._counter_path.is_file():
                try:
                    counter = int(json.loads(self._counter_path.read_text(encoding="utf-8")).get("next", 0))
                except (OSError, TypeError, ValueError, json.JSONDecodeError):
                    counter = 0
            snapshot_id = f"snapshot-{counter}"
            self._atomic_json(self._counter_path, {"next": counter + 1})
            normalized = {self._key(key): value for key, value in manifests.items()}
            snapshot = ProfileSnapshot(
                snapshot_id=snapshot_id,
                profile=self.profile,
                parent_id=parent,
                revisions={key: int(value.revision) for key, value in normalized.items()},
                manifests=normalized,
            )
            self._atomic_json(
                self.root / f"{snapshot_id}.json",
                snapshot.model_dump(mode="json", by_alias=True),
            )
            self._atomic_json(self._current_path, {"snapshot_id": snapshot_id})
            return snapshot

    async def publish_updates(
        self, updates: Mapping[DataSurface | str, int]
    ) -> ProfileSnapshot:
        """Publish a new logical revision while preserving other manifests."""
        current = self.current()
        manifests: dict[str, SurfaceManifest] = {}
        if current is not None:
            manifests.update(current.manifests)
        for raw_surface, revision in updates.items():
            surface = self._key(raw_surface)
            previous = manifests.get(surface)
            if previous is None:
                try:
                    parsed = DataSurface(surface)
                except ValueError:
                    parsed = DataSurface.WORKSPACE
                previous = SurfaceManifest(surface=parsed)
            manifests[surface] = previous.model_copy(update={"revision": int(revision)})
        return await self.publish(manifests)


__all__ = ["SurfaceManifest", "ProfileSnapshot", "SnapshotStore"]
