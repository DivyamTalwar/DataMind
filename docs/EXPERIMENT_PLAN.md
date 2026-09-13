# DataMind SIGMOD 实验计划（简版）

这份文档用于分工和填结果。每个 RQ 只保留实验条件、指标和结果模板；正式结果必须保存 task-level trace。

## 当前可执行性

| 部分 | 当前状态 | 现在能得到什么 |
|---|---|---|
| DataMind 代码回归 | 可直接运行 | `pytest -q`：两代理、格式解析、ledger、candidate/snapshot、read guard |
| 通用 serving smoke test | 可直接运行 | `python -m benchmark.run` 生成 JSONL；需要配置模型 API 和自定义问题集 |
| RQ1 WorkSurface-Bench 全量 | 还不能直接运行 | 缺 benchmark 数据适配、gold surface 解析、Route/Evidence 评分和多条件 sweep |
| RQ2 WorkSurface-Build | 还不能直接运行 | 缺 Document/Table/Graph/Eager/Heuristic/DataMind-build 的统一 driver 和成本采集 |
| RQ3 runtime performance | 可做 serving benchmark | 通用 runner 已有并发和 latency；缺 RSS 采集、no-hooks sweep 和结果聚合脚本 |
| RQ4 fault injection | 只能测局部路径 | 已有 MinerU→pypdf fallback 和结构化 tool errors；缺统一故障注入、结果归一化和 fault matrix runner |

因此，在没有补齐实验 harness 前，不应把 smoke test 或单元测试写成论文结果。论文中的 RQ 表格只有在相应 adapter、driver 和 scorer 完成后才填入数字。

## RQ 之间的代码耦合

RQ1--RQ4 不需要做成一套统一的大型实验平台，可以由不同同学分别实现并直接产出自己的表格结果。它们共享的只有现有 DataMind runtime、模型配置、输入数据版本，以及结果中最基本的 task id、condition、answer、latency、tool trace 和 evidence 字段。

| 实验 | 主要依赖 | 是否依赖其他 RQ |
|---|---|---|
| RQ1 | `benchmark/run.py`、WorkSurface-Bench adapter、serving scorer | 否 |
| RQ2 | ingest/build service、WorkSurface-Build workspace、成本统计 | 否；构建出的数据可选地复用于 RQ1 |
| RQ3 | `benchmark/run.py`、hooks 配置、并发参数、进程资源监控 | 否 |
| RQ4 | parser/DB/Graph fault injection、结构化错误日志 | 否 |

每位同学只需要负责自己的 driver、结果表和最小验证脚本。不要为了实验去重构 DataMind 核心；如果必须修改共享 runtime，先保持接口兼容，并在自己的 RQ 目录下记录所需配置。最终只需把四组已经生成的表格和图汇总到论文中。

## DataMind 和 DataMind-build

**DataMind** 是面向 tool-using agent 的 workspace data plane。它把同一组原始文件组织成 document、table、graph、memory 等 surface，并在 serving 时通过 manifest、profile、snapshot、receipt 和 revision 管理这些数据。Serving Agent 读取的是一个明确的 profile snapshot，因此可以知道数据来自哪个版本、哪个 source，以及结果是否可审计；如果内置 live-only provider 已经无法满足这个 snapshot，运行时会 fail-closed，而不是返回混合版本结果。

**DataMind-build** 是 DataMind 的入库方向（Build Agent），不是另一套系统。它从 workspace 开始，检查 source 和 manifest，构建 document/database/graph surfaces，把结果记录为 candidate revision，完成 validation，生成 receipts，最后发布新的 profile snapshot。memory 和 skills 是独立的 profile-scoped runtime surfaces。RQ2 中它和 `Eager-all / unmanaged-all` 使用相同的 surface、parser 和 backend，区别在于 DataMind-build 管理完整生命周期，而 unmanaged pipeline 直接把结果写入 backend。

## 统一设置

**数据**

- RQ1：WorkSurface-Bench 全部 1,151 个任务，覆盖 RAG、Table、Graph、Cross-surface。
- RQ2：对应的五个 persona workspace，从原始文件开始构建 surface。
- RQ3：固定 serving workload 和并发度；RQ4：固定 workspace 和故障注入脚本。

**模型**

| 实验 | 模型 |
|---|---|
| RQ1 主实验 | GPT-4o-mini、DeepSeek-V4-Pro、Gemini-3.1-Pro、GPT-5.5 |
| RQ2 | Build Agent 和 Serving Worker 固定 GPT-5.5 |
| RQ3/RQ4 | 以确定性 workload 为主；需要端到端答案时固定 GPT-5.5 |

固定 model ID、prompt、tool schema、temperature、task order、timeout、DataMind commit 和数据版本。主结果每个条件跑一次；分层 200-task 子集重复三次并报告 95% bootstrap CI。

**Serving 条件**

| 条件 | 含义 |
|---|---|
| No-tool | 不开放 workspace 工具 |
| Always-RAG | 只开放 document surface |
| Naive-router | 所有 surface 可用，但没有 DataMind snapshot/receipt |
| ReAct-all | 所有原始工具直接暴露，模型自行探索 |
| DataMind-full | manifest、receipt、candidate publication、snapshot pinning 和 fail-closed guard 开启；解析器使用 MinerU API，失败时回退 pypdf |
| Gold-constrained | 只开放 gold 所需 surface，作为 routing upper bound |
| Gold-hint/all | 所有工具开放，但 prompt 给出 gold surface hint |

## RQ1：Surface-aware serving 是否改善质量和效率？

**运行：** 四个模型运行 ReAct-all、Naive-router、DataMind-full、Gold-constrained、Gold-hint/all；同时复现 No-tool 和 Always-RAG。分别报告 RAG、Table、Graph、Cross-surface。

**外部系统对比：** 保留 DB-GPT 和 RAGFlow，但只在它们真正支持且能使用相同模型、相同数据、相同问题和相同输出预算的任务子集上比较。DB-GPT 主要作为 database/structured subset 的端到端基线；RAGFlow 主要作为 document/RAG subset 的基线。不要把只支持单一 surface 的系统与 DataMind 在 Cross-surface 上的总分直接比较。若部署版本、模型或数据处理链无法对齐，则只保留论文 Table 1 的定性能力矩阵和系统说明，不填入定量主表。

**指标：** Route Precision/Recall/F1、Evidence、Answer、Efficiency、tool calls、irrelevant calls、invalid calls、tokens、p50/p95 latency。receipt completeness 只保留在原始 trace 中，不作为 RQ1 主结果。

**Table RQ1-A：主结果**

| Model | Condition | Route-F1 | Evidence | Answer | Efficiency | Tokens | p95 Latency |
|---|---|---:|---:|---:|---:|---:|---:|
| GPT-4o-mini | ReAct-all |  |  |  |  |  |  |
| GPT-4o-mini | DataMind-full |  |  |  |  |  |  |
| DeepSeek-V4-Pro | ReAct-all |  |  |  |  |  |  |
| DeepSeek-V4-Pro | DataMind-full |  |  |  |  |  |  |
| Gemini-3.1-Pro | ReAct-all |  |  |  |  |  |  |
| Gemini-3.1-Pro | DataMind-full |  |  |  |  |  |  |
| GPT-5.5 | ReAct-all |  |  |  |  |  |  |
| GPT-5.5 | DataMind-full |  |  |  |  |  |  |

**Table RQ1-C：外部系统匹配子集（可选）**

| System | Matched subset | Route-F1 | Evidence | Answer | p95 Latency | Errors |
|---|---|---:|---:|---:|---:|---:|
| DB-GPT | Table/SQL |  |  |  |  |  |
| RAGFlow | RAG/document |  |  |  |  |  |
| DataMind-full | Same subset |  |  |  |  |  |

**Table RQ1-B：按任务类型**

| Condition | RAG Answer | Table Answer | Graph Answer | Cross Answer | Evidence |
|---|---:|---:|---:|---:|---:|
| ReAct-all |  |  |  |  |  |
| Naive-router |  |  |  |  |  |
| DataMind-full |  |  |  |  |  |
| Gold-hint/all |  |  |  |  |  |

**图：**

- RQ1-Fig-A：Quality–efficiency frontier，x=Tokens 或 p95 Latency，y=Answer。
- RQ1-Fig-B：Failure decomposition，展示 wrong route、missing evidence、invalid call、backend error、synthesis error。

## RQ2：构建多种 surface 的成本何时摊平？

**策略：** Document-only、Table-only、Graph-only、Eager-all、Heuristic-demand、DataMind-build。Build Agent 和 serving Worker 均固定 GPT-5.5，使用相同原始文件、checksum 和解析配置。

这里的名称指“如何建库”，不要和 RQ1 的 `ReAct-all`（如何调用工具）混淆：

| 策略 | 定义 | 实验意义 |
|---|---|---|
| Document-only | 把 workspace 中的内容统一解析并构建为 document/RAG surface；不构建 table 和 graph projection | 低构建成本的单 surface baseline；所有问题都只能走文档表示 |
| Table-only | 只构建 typed table/view | 测量结构化数据单独建库的成本和能力 |
| Graph-only | 只构建 graph/lineage surface | 测量关系数据单独建库的成本和能力 |
| Eager-all / unmanaged-all | 对每个 workspace 一次性构建 document、table、graph（以及启用的 memory）surface；使用与 DataMind 相同的 parser/backend，但没有 manifest 驱动、candidate validation、receipt、snapshot publication 或 profile revision | 与 DataMind 构建相同内容，用来隔离数据面编排和一致性语义的成本 |
| Heuristic-demand | 用预先固定的规则，根据文件类型或离线 workload 选择要建的 surface | 低成本 demand-aware baseline，但没有 DataMind 的 snapshot/receipt 语义 |
| DataMind-build | Build Agent 构建相同的 configured surfaces，但通过 manifest、candidate validation、receipt、publication 和 revision 管理完成 | 完整的数据面构建流程 |

Document-only 不是“只处理 .docx 文件”：CSV、XLSX、PDF 等输入也要被纳入同一 document 表示，确保比较的是 surface 选择，而不是输入文件过滤。Eager-all 也不是把工具全部暴露给模型，而是在 build 阶段预先物化所有 surface。由于 DataMind 当前的目标也是构建所有 configured surfaces，RQ2 中 Eager-all 与 DataMind-build 必须使用相同输入、parser 和 backend；二者的差别是 DataMind 的 manifest、receipt、validation、snapshot 和 revision 语义，而不是 surface 数量。

**指标：**

- Build：build time、API/LLM calls、storage、peak memory、source coverage、provenance completeness、duplicate rate、validation failures。
- Serving：Answer、Evidence、Efficiency、p95 latency、cost/query。

计算 C(N) = C_build + N × C_serve，N 取 0、10、50、100、500、1,000、5,000。

**Table RQ2-A：构建成本**

| Strategy | Build Time | API/LLM Calls | Storage | Coverage | Provenance | Validation Failures |
|---|---:|---:|---:|---:|---:|---:|
| Document-only |  |  |  |  |  |  |
| Eager-all |  |  |  |  |  |  |
| DataMind-build |  |  |  |  |  |  |

**Table RQ2-B：构建后的 serving 价值**

| Strategy | N | Answer | Evidence | Efficiency | p95 Latency | Cost/Query |
|---|---:|---:|---:|---:|---:|---:|
| Document-only | 100 |  |  |  |  |  |
| Eager-all | 100 |  |  |  |  |  |
| DataMind-build | 100 |  |  |  |  |  |

**图：** RQ2-Fig-A 累计成本摊平曲线；RQ2-Fig-B 构建时间分解；RQ2-Fig-C quality–cost frontier。

## RQ3：DataMind 的运行时开销和并发性能

RQ3 不再比较 Mutable/Ledger-only/Snapshot-only，也不把 snapshot 或 receipt
作为独立变量。它只测 DataMind 在相同任务和相同模型下的端到端系统代价。

**条件：**

| 条件 | 含义 |
|---|---|
| DataMind no-hooks | DataMind 完整 serving path，但关闭 PathAllowlist、DestructiveSQL 和 AuditLog hooks |
| DataMind full | 当前默认配置，启用 hooks、evidence、snapshot metadata 和审计路径 |
| DB-GPT（可选） | 只有在能用同一模型、同一任务和同一数据稳定复现时才加入；否则不强行比较外部系统 |

`DataMind no-hooks` 和 `DataMind full` 使用同一组 surface、同一模型、同一
prompt、同一 tool schema 和同一并发度。这样测到的是 DataMind 的安全、审计和
版本语义带来的运行时开销，而不是模型差异。

**运行：** 固定 60 或 200 个代表性任务，分别使用并发度 1、5、20、50、100
运行；记录成功、错误和超时。每个条件至少重复三次。QPS 由完成任务数除以
wall-clock time 计算；峰值 RSS 用进程监控工具记录。

**指标：** Errors、p50/p95/p99 end-to-end latency、QPS、Peak RSS、tool calls、
input/output tokens 和 model/tool latency 分解。错误率单独报告，不与延迟平均。

**Table RQ3：**

| System | N | Errors ↓ | p50 ms ↓ | p95 ms ↓ | p99 ms ↓ | QPS ↑ | Peak RSS MB ↓ |
|---|---:|---:|---:|---:|---:|---:|---:|
| DataMind no-hooks |  |  |  |  |  |  |  |
| DataMind full |  |  |  |  |  |  |  |
| DB-GPT (optional) |  |  |  |  |  |  |  |

**图：** RQ3-Fig-A latency CDF；RQ3-Fig-B throughput–concurrency 曲线；RQ3-Fig-C
latency breakdown（model、tool、hooks、serialization）。

## RQ4：故障时能否恢复且保持可审计？

**故障：** parser failure、MinerU timeout、embedding outage、empty retrieval、
database/SQL timeout、database connection failure、schema/view corruption、
graph unavailable、corrupted artifact、interrupted build、policy violation。

**Baseline：** Retry-only、Fixed-path structured errors、DataMind-full。

**指标：** completion rate、Answer、auditable-answer rate、unsafe answer rate、structured-error classification accuracy、parser fallback success、candidate/read-block correctness、recovery latency。

只有“答案正确 + receipt 合法 + revision 正确”才算恢复成功。

**Table RQ4：**

| Fault | System | Completion | Answer | Auditable | Structured Error | Fallback/Block Correct | Recovery Time |
|---|---|---:|---:|---:|---:|---:|---:|
| Parser/MinerU failure | Retry-only |  |  |  |  |  |  |
| Parser/MinerU failure | DataMind-full |  |  |  |  |  |  |
| Database/SQL timeout | Retry-only |  |  |  |  |  |  |
| Database/SQL timeout | DataMind-full |  |  |  |  |  |  |
| Active candidate read | Retry-only |  |  |  |  |  |  |
| Active candidate read | DataMind-full |  |  |  |  |  |  |
| Graph unavailable | Retry-only |  |  |  |  |  |  |
| Graph unavailable | DataMind-full |  |  |  |  |  |  |

**图：** RQ4-Fig-A structured-error / fallback / block outcome；RQ4-Fig-B recovery latency。

## 统一日志

每个 task 保存以下字段（内部 surface 名称使用 `kb`、`db`、`graph`、`memory`）：

~~~json
{
  "rq": "RQ1",
  "condition": "datamind_full",
  "model": "GPT-5.5",
  "task_id": "...",
  "profile_id": "...",
  "snapshot_id": "...",
  "required_surfaces": ["db", "graph"],
  "accessed_surfaces": ["db", "graph"],
  "route_f1": 1.0,
  "evidence": 1.0,
  "answer": 1.0,
  "tool_calls": 4,
  "invalid_calls": 0,
  "input_tokens": 0,
  "output_tokens": 0,
  "latency_ms": 0,
  "receipt_ids": [],
  "error": null,
  "git_commit": "..."
}
~~~

目录：

~~~text
results/rq1/{raw,normalized,tables,figures}
results/rq2/{raw,normalized,tables,figures}
results/rq3/{raw,normalized,tables,figures}
results/rq4/{raw,normalized,tables,figures}
configs/
scripts/
~~~

## 分工

- 同学 A：RQ1，benchmark adapter、serving sweep、Route/Evidence/Answer 评分。
- 同学 B：RQ2，WorkSurface-Build、构建策略、MinerU/pypdf、成本和摊平曲线。
- 同学 C：RQ3，no-hooks/full serving sweep、并发运行、latency/QPS/RSS 统计。
- 同学 D：RQ4，fault injection、fallback、rollback、receipt audit。

统一日志 schema、统计和表格格式由四组共同遵守。

## 执行顺序

1. 先运行 `pytest -q`，确认代码和快照原语通过；
2. 准备统一的 WorkSurface-Bench adapter、gold parser 和 Route/Evidence scorer；
3. 实现 RQ2 的构建策略 driver，以及 RQ3/RQ4 的确定性 driver；
4. 用 20 个任务跑通所有已实现条件和日志；
5. 锁定 prompt、model ID、tool schema、数据版本和 commit；
6. 跑 RQ1 全量，再并行跑 RQ2、RQ3、RQ4；
7. 跑 200-task 三重复 robustness，自动生成最终表格和图。
