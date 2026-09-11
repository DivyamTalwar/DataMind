from pathlib import Path

import pytest

from datamind.capabilities.ingest.service import IngestService
from datamind.core.errors import CapabilityError


class _Model:
    async def generate_text(self, prompt: str, **kwargs) -> str:
        return '[{"subject":"Alice","relation":"works_on","object":"Project X"}]'


class _Store:
    def __init__(self):
        self.triples = []

    async def upsert_triples(self, triples):
        self.triples.extend(triples)

    async def persist(self):
        return None


class _Graph:
    def __init__(self):
        self.store = _Store()


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
