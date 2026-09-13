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
from .errors import CapabilityError


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


class CandidateSnapshot(BaseModel):
    """Private build candidate waiting for validation and publication."""

    candidate_id: str
    profile: str
    base_snapshot_id: str | None = None
    revisions: dict[str, int] = Field(default_factory=dict)
    status: str = "building"
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

    def assert_readable(self, snapshot_id: str | None, surface: DataSurface | str) -> None:
        """Fail closed when a provider cannot open an historical snapshot.

        The built-in providers currently expose one live view.  A request that
        was pinned before publication must therefore never read that live view
        accidentally.  Providers with historical adapters can replace this
        check with a snapshot-specific view in a future implementation.
        """
        key = self._key(surface)
        # A provider may write its live files while a build candidate is being
        # assembled.  Block reads for touched surfaces until the candidate is
        # validated and published, preventing pre-publication leakage.
        for candidate_path in self.root.glob("candidate-*.json"):
            try:
                candidate = CandidateSnapshot.model_validate(
                    json.loads(candidate_path.read_text(encoding="utf-8"))
                )
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                continue
            if candidate.status == "building" and key in candidate.revisions:
                raise CapabilityError(
                    key,
                    f"surface is being rebuilt by {candidate.candidate_id}; "
                    "reads are blocked until publication",
                )
        if not snapshot_id:
            return
        current_id = self.current_id
        if current_id and snapshot_id != current_id:
            raise CapabilityError(
                key,
                f"snapshot {snapshot_id!r} is no longer current; historical reads "
                "are unavailable for this provider",
            )

    def get(self, snapshot_id: str) -> ProfileSnapshot:
        return self._read_snapshot(snapshot_id)

    def _candidate_path(self, candidate_id: str) -> Path:
        if not candidate_id.startswith("candidate-"):
            raise ValueError(f"invalid candidate id: {candidate_id}")
        return self.root / f"{candidate_id}.json"

    def candidate(self, candidate_id: str) -> CandidateSnapshot:
        path = self._candidate_path(candidate_id)
        if not path.is_file():
            raise FileNotFoundError(f"unknown candidate: {candidate_id}")
        return CandidateSnapshot.model_validate(json.loads(path.read_text(encoding="utf-8")))

    async def begin_candidate(self) -> CandidateSnapshot:
        async with self._lock:
            counter_doc: dict[str, Any] = {}
            if self._counter_path.is_file():
                try:
                    counter_doc = json.loads(self._counter_path.read_text(encoding="utf-8"))
                except (OSError, TypeError, json.JSONDecodeError):
                    counter_doc = {}
            counter = 0
            try:
                counter = int(counter_doc.get("next_candidate", 0))
            except (TypeError, ValueError):
                counter = 0
            candidate_id = f"candidate-{counter}"
            state = CandidateSnapshot(
                candidate_id=candidate_id,
                profile=self.profile,
                base_snapshot_id=self.current_id,
            )
            counter_doc["next_candidate"] = counter + 1
            self._atomic_json(self._counter_path, counter_doc)
            self._atomic_json(self._candidate_path(candidate_id), state.model_dump(mode="json"))
            return state

    async def record_candidate_updates(
        self, candidate_id: str, updates: Mapping[DataSurface | str, int]
    ) -> CandidateSnapshot:
        async with self._lock:
            state = self.candidate(candidate_id)
            if state.status != "building":
                raise ValueError(f"candidate is not building: {state.status}")
            revisions = dict(state.revisions)
            for raw_surface, revision in updates.items():
                key = self._key(raw_surface)
                revisions[key] = int(revision)
            state = state.model_copy(update={"revisions": revisions})
            self._atomic_json(self._candidate_path(candidate_id), state.model_dump(mode="json"))
            return state

    async def validate_candidate(self, candidate_id: str) -> CandidateSnapshot:
        async with self._lock:
            state = self.candidate(candidate_id)
            if state.status != "building":
                if state.status == "validated":
                    return state
                raise ValueError(f"candidate is not building: {state.status}")
            if any(int(revision) < 0 for revision in state.revisions.values()):
                raise ValueError("candidate contains an invalid negative revision")
            if not state.revisions:
                raise ValueError("candidate has no surface revisions")
            state = state.model_copy(update={"status": "validated"})
            self._atomic_json(self._candidate_path(candidate_id), state.model_dump(mode="json"))
            return state

    async def publish_candidate(self, candidate_id: str) -> ProfileSnapshot:
        async with self._lock:
            state = self.candidate(candidate_id)
            if state.status != "validated":
                raise ValueError(f"candidate must be validated before publish: {state.status}")
            current = self.current()
            manifests: dict[str, SurfaceManifest] = {}
            if current is not None:
                manifests.update(current.manifests)
            for surface, revision in state.revisions.items():
                previous = manifests.get(surface)
                if previous is None:
                    previous = SurfaceManifest(surface=DataSurface(surface))
                manifests[surface] = previous.model_copy(update={"revision": int(revision)})
            # Publish inline while holding the same lock to keep candidate
            # validation and current-pointer advancement atomic.
            parent = current.snapshot_id if current else state.base_snapshot_id
            counter = 0
            if self._counter_path.is_file():
                try:
                    counter = int(json.loads(self._counter_path.read_text(encoding="utf-8")).get("next", 0))
                except (OSError, TypeError, ValueError, json.JSONDecodeError):
                    counter = 0
            snapshot_id = f"snapshot-{counter}"
            counter_doc = {}
            if self._counter_path.is_file():
                try:
                    counter_doc = json.loads(self._counter_path.read_text(encoding="utf-8"))
                except (OSError, TypeError, json.JSONDecodeError):
                    counter_doc = {}
            counter_doc["next"] = counter + 1
            self._atomic_json(self._counter_path, counter_doc)
            snapshot = ProfileSnapshot(
                snapshot_id=snapshot_id,
                profile=self.profile,
                parent_id=parent,
                revisions={key: int(value.revision) for key, value in manifests.items()},
                manifests=manifests,
            )
            self._atomic_json(self.root / f"{snapshot_id}.json", snapshot.model_dump(mode="json", by_alias=True))
            self._atomic_json(self._current_path, {"snapshot_id": snapshot_id})
            state = state.model_copy(update={"status": "published"})
            self._atomic_json(self._candidate_path(candidate_id), state.model_dump(mode="json"))
            return snapshot

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
            counter_doc: dict[str, Any] = {}
            if self._counter_path.is_file():
                try:
                    counter_doc = json.loads(self._counter_path.read_text(encoding="utf-8"))
                except (OSError, TypeError, json.JSONDecodeError):
                    counter_doc = {}
            counter_doc["next"] = counter + 1
            self._atomic_json(self._counter_path, counter_doc)
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


__all__ = ["SurfaceManifest", "ProfileSnapshot", "CandidateSnapshot", "SnapshotStore"]
