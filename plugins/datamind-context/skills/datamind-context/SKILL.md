---
name: datamind-context
description: Use DataMind from Codex to ingest local files, query RAG or graph knowledge, store facts, and inspect profiles.
---

# DataMind Context

Use this skill when the user asks Codex to use DataMind, ingest a local file or
folder, query indexed knowledge, ask about relationships, remember a preference,
or inspect profiles.

Prefer these tools:

- `datamind_use_folder` to add a file or directory.
- `datamind_ask` for an evidence-backed answer across DataMind surfaces.
- `datamind_rag_query` for direct document search.
- `datamind_graph_query` for relationship and multi-hop questions.
- `datamind_store` for conversational writes that should be routed by StoreAgent.
- `datamind_remember` for an explicit durable preference, decision, or fact.
- `datamind_list_profiles` and `datamind_status` to inspect local state.

The plugin is an adapter to the DataMind v1 runtime. Do not assume that it has
an independent database, index, or memory store. Keep user source files intact;
DataMind's ingest tools copy or index them according to the active profile and
path safety policy.
