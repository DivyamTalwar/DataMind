# DataMind Context for Codex

This directory is the official Codex adapter shipped with the DataMind repository.
It connects Codex to the current `datamind` v1 runtime over MCP; it does not
contain a second RAG engine, model client, or storage implementation.

## Install from a DataMind checkout

```bash
cd /path/to/DataMind
./scripts/install_codex_plugin.sh
```

The installer creates the Codex local marketplace entry and installs the current
DataMind package into the repository virtual environment. Edit the generated
`.env.datamind` file, or set the `DATAMIND__LLM__*` and
`DATAMIND__EMBEDDING__*` variables before first use.

## What the plugin exposes

- `datamind_ask` — query through RetrieveAgent and return evidence.
- `datamind_store` — write through StoreAgent and return receipts.
- `datamind_use_folder` — ingest a file or directory through the KB ingest tools.
- `datamind_rag_query` — perform direct vector search.
- `datamind_graph_query` — ask a relationship question using graph tools.
- `datamind_remember` — save durable memory.
- `datamind_list_profiles` and `datamind_status` — inspect local state.

For the complete tutorial, configuration reference, and deployment guidance,
see the [DataMind documentation site](https://opendcai.github.io/DataMind-Doc/).
