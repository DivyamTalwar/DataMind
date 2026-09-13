from pathlib import Path

import pytest

from datamind.core.contracts import DataSurface
from datamind.core.snapshots import SnapshotStore, SurfaceManifest
from datamind.agent.options import AgentServices, StoreAgent


@pytest.mark.asyncio
async def test_snapshot_store_publishes_immutable_profile_views(tmp_path: Path):
    store = SnapshotStore(storage_dir=tmp_path / "storage", profile="demo")
    initial = await store.ensure_initial({
        DataSurface.KB: SurfaceManifest(
            surface=DataSurface.KB,
            operations=["kb_search"],
            revision=0,
        ),
        DataSurface.DB: SurfaceManifest(surface=DataSurface.DB, revision=0),
    })
    assert initial.snapshot_id == "snapshot-0"
    assert store.current_id == initial.snapshot_id

    updated = await store.publish_updates({"kb": 3})
    assert updated.snapshot_id == "snapshot-1"
    assert updated.parent_id == initial.snapshot_id
    assert updated.revisions == {"kb": 3, "db": 0}

    # Earlier snapshots remain readable after publication.
    assert store.get(initial.snapshot_id).revisions["kb"] == 0
    assert store.current().snapshot_id == updated.snapshot_id


def test_surface_manifest_serializes_schema_alias():
    manifest = SurfaceManifest(surface=DataSurface.DB, schema={"tables": ["orders"]})
    assert manifest.model_dump(mode="json", by_alias=True)["schema"] == {
        "tables": ["orders"]
    }


@pytest.mark.asyncio
async def test_store_agent_publishes_receipt_revision(tmp_path: Path):
    snapshots = SnapshotStore(storage_dir=tmp_path / "storage", profile="demo")
    await snapshots.ensure_initial({DataSurface.KB: SurfaceManifest(surface=DataSurface.KB)})

    class _Loop:
        async def run_turn(self, **kwargs):
            return {"answer": "ok", "receipts": [{
                "revision": 4,
                "results": [{"status": "stored", "surface": "kb"}],
            }]}

    agent = StoreAgent(
        services=AgentServices(client=None, fallback_client=None, snapshots=snapshots),  # type: ignore[arg-type]
        tools=None,  # type: ignore[arg-type]
        loop=_Loop(),  # type: ignore[arg-type]
        ledger=None,  # type: ignore[arg-type]
    )
    result = await agent.store("write")
    assert result["snapshot_id"] == "snapshot-1"
    assert snapshots.current().revisions["kb"] == 4
