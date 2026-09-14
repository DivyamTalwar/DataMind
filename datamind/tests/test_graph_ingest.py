from pathlib import Path

import pytest

from datamind.capabilities.ingest.service import IngestService, _infer_table_name
from datamind.core.errors import CapabilityError


@pytest.mark.parametrize(
    ("stem", "expected"),
    [
        ("03-customers-2026", "t_03_customers_2026"),
        ("sales-pipeline-q2", "sales_pipeline_q2"),
        ("", "table"),
    ],
)
def test_infer_table_name_normalizes_filename_stems(stem: str, expected: str):
    assert _infer_table_name(stem) == expected


class _Model:
    async def generate_text(self, prompt: str, **kwargs) -> str:
        return '[{"subject":"Alice","relation":"works_on","object":"Project X"}]'


class _Store:
    def __init__(self):
        self.triples = []

    async def upsert_triples(self, triples):
        self.triples.extend(triples)

    async def reconcile_lineage_triples(self, root, triples):
        self.triples = [
            item for item in self.triples
            if item.properties.get("_lineage_root") != root
        ]
        self.triples.extend(triples)

    async def persist(self):
        return None


class _Graph:
    def __init__(self):
        self.store = _Store()


def _service(tmp_path: Path) -> IngestService:
    return IngestService(
        kb=None,
        db=None,
        graph=_Graph(),
        llm_client=_Model(),
        llm_model="test",
        profile_data_dir=tmp_path / "profile",
        chunk_size=512,
        chunk_overlap=64,
    )


@pytest.mark.asyncio
async def test_workspace_inspect_reports_hashes_and_surface_candidates(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "notes.md").write_text("hello", encoding="utf-8")
    (workspace / "orders.xlsx").write_bytes(b"fixture")
    (workspace / "image.png").write_bytes(b"fixture")

    result = await _service(tmp_path).workspace_inspect(path=str(workspace))

    assert result["files_scanned"] == 3
    assert result["by_extension"] == {".md": 1, ".png": 1, ".xlsx": 1}
    assert result["by_surface"]["kb"] == 2
    assert result["by_surface"]["db"] == 1
    notes = next(item for item in result["files"] if item["path"].endswith("notes.md"))
    assert notes["relative_path"] == "notes.md"
    assert notes["sha256"].startswith("sha256:")
    assert notes["candidate_surfaces"] == ["kb", "graph_text"]


@pytest.mark.asyncio
async def test_workspace_inspect_caps_file_listing(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    for name in ("a.md", "b.md", "c.md"):
        (workspace / name).write_text(name, encoding="utf-8")

    result = await _service(tmp_path).workspace_inspect(
        path=str(workspace), include_hash=False, max_files=2
    )

    assert result["files_total"] == 3
    assert result["files_scanned"] == 2
    assert result["truncated"] is True
    assert all(item["sha256"] is None for item in result["files"])


@pytest.mark.asyncio
async def test_graph_build_lineage_adds_deterministic_file_relations(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "report.md").write_text("See source.csv", encoding="utf-8")
    (workspace / "source.csv").write_text("item,cost\na,1\n", encoding="utf-8")
    (workspace / "source-v2.csv").write_text("item,cost\nb,2\n", encoding="utf-8")
    (workspace / "duplicate.txt").write_text("same", encoding="utf-8")
    (workspace / "copy.txt").write_text("same", encoding="utf-8")

    graph = _Graph()
    service = IngestService(
        kb=None,
        db=None,
        graph=graph,
        llm_client=_Model(),
        llm_model="test",
        profile_data_dir=tmp_path / "profile",
        chunk_size=512,
        chunk_overlap=64,
    )
    result = await service.graph_build_lineage(path=str(workspace))
    relations = {triple.relation for triple in graph.store.triples}

    assert result["files_processed"] == 5
    assert {"contains", "mentions", "schema_overlap", "version_of", "shared_artifact"} <= relations
    assert all(triple.properties["_lineage_root"] == str(workspace) for triple in graph.store.triples)


@pytest.mark.asyncio
async def test_build_lifecycle_freezes_verifies_and_exports_artifacts(tmp_path: Path):
    base = tmp_path / "project"
    profile = base / "data" / "profiles" / "default"
    workspace = tmp_path / "workspace"
    profile.mkdir(parents=True)
    workspace.mkdir()
    (workspace / "notes.md").write_text("build me", encoding="utf-8")
    storage = base / "storage" / "default"
    storage.mkdir(parents=True)
    (storage / "graph.json").write_text("{}", encoding="utf-8")
    service = IngestService(
        kb=None, db=None, graph=_Graph(), llm_client=_Model(), llm_model="test",
        profile_data_dir=profile, chunk_size=512, chunk_overlap=64,
    )

    started = await service.build_start(path=str(workspace))
    frozen = await service.build_freeze(build_id=started["build_id"])
    assert frozen["status"] == "FROZEN"
    assert (profile / "builds" / started["build_id"] / "manifest.json").is_file()
    assert (await service.build_verify(build_id=started["build_id"]))["ok"] is True

    output = tmp_path / "export"
    exported = await service.build_export(build_id=started["build_id"], output_path=str(output))
    assert exported["artifacts_exported"] >= 1
    assert (output / "storage" / "graph.json").read_text(encoding="utf-8") == "{}"


@pytest.mark.asyncio
async def test_graph_add_path_extracts_each_text_file_with_source(tmp_path: Path):
    source_dir = tmp_path / "docs"
    source_dir.mkdir()
    (source_dir / "a.md").write_text("Alice owns Project X", encoding="utf-8")
    (source_dir / "b.txt").write_text("Alice owns Project Y", encoding="utf-8")
    (source_dir / "ignored.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    graph = _Graph()
    service = IngestService(
        kb=None,
        db=None,
        graph=graph,
        llm_client=_Model(),
        llm_model="test",
        profile_data_dir=tmp_path / "profile",
        chunk_size=512,
        chunk_overlap=64,
    )

    result = await service.graph_add_path(path=str(source_dir))

    assert result["files_processed"] == 2
    assert result["triples_added"] == 2
    assert result["skipped_count"] == 0
    assert {triple.source for triple in graph.store.triples} == {
        str(source_dir / "a.md"), str(source_dir / "b.txt")
    }


@pytest.mark.asyncio
async def test_graph_add_path_rejects_unsupported_single_file(tmp_path: Path):
    source = tmp_path / "data.csv"
    source.write_text("a,b\n1,2\n", encoding="utf-8")
    service = IngestService(
        kb=None,
        db=None,
        graph=_Graph(),
        llm_client=_Model(),
        llm_model="test",
        profile_data_dir=tmp_path / "profile",
        chunk_size=512,
        chunk_overlap=64,
    )

    with pytest.raises(CapabilityError, match="unsupported extension"):
        await service.graph_add_path(path=str(source))

@pytest.mark.asyncio
async def test_raw_file_read_is_paginated_and_hashed(tmp_path: Path):
    source = tmp_path / "evidence.md"
    source.write_text("abcdef", encoding="utf-8")
    service = _service(tmp_path)
    page = await service.raw_file_read(path=str(source), offset=2, max_chars=3)
    assert page["text"] == "cde"
    assert page["next_offset"] == 5
    assert page["truncated"] is True
    assert page["sha256"].startswith("sha256:")


@pytest.mark.asyncio
async def test_lineage_accepts_explicit_dependencies(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "answer.md").write_text("answer", encoding="utf-8")
    (workspace / "data.csv").write_text("id\n1\n", encoding="utf-8")
    graph = _Graph()
    service = IngestService(kb=None, db=None, graph=graph, llm_client=_Model(), llm_model="test",
                            profile_data_dir=tmp_path / "profile", chunk_size=512, chunk_overlap=64)
    result = await service.graph_build_lineage(path=str(workspace), dependencies=[{"source": "answer.md", "target": "data.csv"}])
    assert result["relations"]["depends_on"] == 1


@pytest.mark.asyncio
async def test_build_status_reports_frozen_verification(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "notes.md").write_text("x", encoding="utf-8")
    service = _service(tmp_path)
    started = await service.build_start(path=str(workspace))
    assert (await service.build_status(build_id=started["build_id"]))["status"] == "BUILDING"
    await service.build_freeze(build_id=started["build_id"])
    status = await service.build_status(build_id=started["build_id"])
    assert status["status"] == "FROZEN"
    assert status["verification"]["ok"] is True
