# DataMind SIGMOD 实验计划（简版）

这份文档用于分工和填结果。每个 RQ 只保留实验条件、指标和结果模板；正式结果必须保存 task-level trace。

## DataMind 和 DataMind-build

**DataMind** 是面向 tool-using agent 的 workspace data plane。它把同一组原始文件组织成 document、table、graph、memory 等 surface，并在 serving 时通过 manifest、profile、snapshot、receipt 和 revision 管理这些数据。Serving Agent 读取的是一个明确的 profile snapshot，因此可以知道数据来自哪个版本、哪个 source，以及结果是否可审计；如果内置 live-only provider 已经无法满足这个 snapshot，运行时会 fail-closed，而不是返回混合版本结果。

**DataMind-build** 是 DataMind 的入库方向（Build Agent），不是另一套系统。它从 workspace 开始，检查 source 和 manifest，构建 document/database/graph surfaces，把结果记录为 candidate revision，完成 validation，生成 receipts，最后发布新的 profile snapshot。memory 和 skills 是独立的 profile-scoped runtime surfaces。RQ2 中它和 `Eager-all / unmanaged-all` 使用相同的 surface、parser 和 backend，区别在于 DataMind-build 管理完整生命周期，而 unmanaged pipeline 直接把结果写入 backend。

## 统一设置

**数据**

- RQ1：WorkSurface-Bench 全部 1,151 个任务，覆盖 RAG、Table、Graph、Cross-surface。
- RQ2：对应的五个 persona workspace，从原始文件开始构建 surface。
- RQ3/RQ4：固定 workspace、更新脚本和故障注入脚本。

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

**指标：** Route Precision/Recall/F1、Evidence、Answer、Efficiency、tool calls、irrelevant calls、invalid calls、tokens、p50/p95 latency、receipt completeness。

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

**Table RQ1-B：按任务类型**

| Condition | RAG Answer | Table Answer | Graph Answer | Cross Answer | Evidence |
|---|---:|---:|---:|---:|---:|
| ReAct-all |  |  |  |  |  |
| Naive-router |  |  |  |  |  |
| DataMind-full |  |  |  |  |  |
| Gold-hint/all |  |  |  |  |  |

**Table RQ1-C：消融**

RQ1 的静态 benchmark 只能可靠测出 manifest 和 evidence receipt。snapshot
只有在数据存在多个 revision 时才有作用，fallback 只有在 backend 故障时才有
作用，因此二者分别放到 RQ3 和 RQ4；不要在静态 RQ1 中把它们当成有效消融。

- **manifest**：surface 的能力描述，包括 schema、可用 operation、source
  范围、freshness、evidence 类型和 cost。移除后，模型只能看到通用工具，
  不能先按能力筛选 surface。主要观察 Route-F1、irrelevant calls 和 tokens。
- **receipt**：每次读写返回的 source、locator、profile、revision 和
  receipt ID。移除后仍可返回值，但没有可审计的来源链。除 benchmark 的
  Evidence 外，必须额外报告 auditable-evidence/receipt completeness，
  否则标准 Evidence 可能无法体现 receipt 的差异。
- **snapshot**：请求绑定的 profile revision 向量；候选正在更新某个 surface
  时阻断该 surface 的读取，已发布版本被请求 supersede 后对 live-only
  provider fail-closed。当前实现不提供旧 artifact 的历史读取。只在 RQ3
  的 add/modify/delete 和并发实验中比较。
- **fallback**：当前实现只对 PDF/office 解析提供 MinerU API 到 pypdf 的确定性
  fallback。surface 故障不会自动切换到另一个 surface；运行时会返回结构化错误，
  由模型决定是否发起另一工具调用。只在 RQ4 fault injection 中比较。

| Variant | Route-F1 | Evidence | Answer | Invalid Calls | Tokens | Receipt Completeness |
|---|---:|---:|---:|---:|---:|---:|
| DataMind-full |  |  |  |  |  |  |
| − manifest |  |  |  |  |  |  |
| − receipt |  |  |  |  |  |  |

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

## RQ3：snapshot、receipt 和 profile isolation 是否成立？

**运行：** 更新类型为 add、modify、delete、replay、concurrent update、partial failure；并发客户端为 1、5、20、50、100；工作负载包括 same-profile read、cross-profile read、concurrent write、80/20 read-write、50/50 read-write。

**Baseline（均为实验中实现的对照版本，不是已有产品名称）：**

这里的 baseline 是为了做机制拆分而定义的 feature ablation，不对应四个
独立产品。当前代码已经有 `IngestLedger`、revision、write receipt、candidate
publication 和请求级 snapshot pinning。由于内置后端暂时没有历史 artifact
读取，RQ3 必须把“候选期间读取阻断”和“过期 snapshot fail-closed”作为正确性
条件；不能把它们报告成旧版本继续可读。

| 版本 | 保留的机制 | 去掉的机制 | 用来回答什么问题 |
|---|---|---|---|
| Mutable pipeline | backend 直接读写 | ledger、receipt、snapshot publication | 没有数据面控制时，stale read、重复写和混合 revision 有多严重？ |
| Ledger-only | ingestion ledger、write receipt、source fingerprint | snapshot publication | ledger 是否能解决重复写和写入审计，但仍允许读到不同 surface 的最新状态？ |
| Snapshot-only | candidate revision、snapshot publication | ledger、idempotent write receipt | snapshot 是否能避免 mixed revision，但无法处理重复 ingestion？ |
| DataMind-full | ledger + receipt + snapshot + profile policy + candidate/read guards | 无 | 完整系统 |

实现时四个版本必须使用同一批数据、同一并发 driver 和同一 backend。只切换上述机制，不能给某个版本额外的锁或重试策略。这样 Mutable→Ledger-only 主要测 idempotence/audit，Snapshot-only→DataMind-full 主要测 ledger 的增益，Ledger-only→DataMind-full 主要测 snapshot publication 的增益。

**指标：** visibility delay、stale-read、mixed-snapshot、duplicate-write、lost-update、cross-profile leakage、throughput、p50/p95/p99 latency。

**Table RQ3：**

| System | Visibility Delay | Stale Reads | Mixed Snapshot | Duplicate Writes | Leakage | Throughput | p95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Mutable pipeline |  |  |  |  |  |  |  |
| Ledger-only |  |  |  |  |  |  |  |
| Snapshot-only |  |  |  |  |  |  |  |
| DataMind-full |  |  |  |  |  |  |  |

**图：** RQ3-Fig-A publication timeline；RQ3-Fig-B throughput–latency curve；RQ3-Fig-C profile isolation heatmap。

## RQ4：故障时能否恢复且保持可审计？

**故障：** parser failure、MinerU timeout、embedding outage、empty retrieval、
database/SQL timeout、database connection failure、schema/view corruption、
graph unavailable、corrupted artifact、interrupted build、policy violation。

**Baseline：** Retry-only、Fixed-path structured errors、DataMind-full。

**指标：** completion rate、Answer、auditable-answer rate、unsafe answer rate、recovery latency、retry count、rebuilt bytes、rollback success、false fallback rate。

只有“答案正确 + receipt 合法 + revision 正确”才算恢复成功。

**Table RQ4：**

| Fault | System | Completion | Answer | Auditable | Recovery Time | Rebuilt Bytes |
|---|---|---:|---:|---:|---:|---:|
| Parser failure | Retry-only |  |  |  |  |  |
| Parser failure | DataMind-full |  |  |  |  |  |
| Database/SQL timeout | Retry-only |  |  |  |  |  |
| Database/SQL timeout | DataMind-full |  |  |  |  |  |
| Database schema corruption | Retry-only |  |  |  |  |  |
| Database schema corruption | DataMind-full |  |  |  |  |  |
| Graph unavailable | Retry-only |  |  |  |  |  |
| Graph unavailable | DataMind-full |  |  |  |  |  |

**图：** RQ4-Fig-A recovery outcome；RQ4-Fig-B recovery time 和 rebuilt bytes。

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
- 同学 C：RQ3，snapshot、ledger、并发 driver、profile isolation。
- 同学 D：RQ4，fault injection、fallback、rollback、receipt audit。

统一日志 schema、统计和表格格式由四组共同遵守。

## 执行顺序

1. 用 20 个任务跑通所有条件和日志；
2. 完成 RQ3/RQ4 的确定性测试；
3. 用 GPT-4o-mini 做 RQ1/RQ2 smoke test；
4. 锁定 prompt、model ID、tool schema、数据版本和 commit；
5. 跑 RQ1 全量，再并行跑 RQ2、RQ3、RQ4；
6. 跑 200-task 三重复 robustness；
7. 自动生成最终表格和图。
