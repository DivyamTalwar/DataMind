# DataMind SIGMOD 实验计划

这份计划按一条数据生命周期组织实验，避免把已有结果拼成彼此独立的 RQ：

```text
Raw workspace
   │
   ▼
RQ2  Build Agent：选择并物化 document / table / graph surfaces
   │  输出同一个 published snapshot（workspace、profile、revision）
   ▼
RQ1  Serving Agent：在该 snapshot 上回答 WorkSurface-Bench
   │  使用同一批 task trace
   ├──────────────► RQ3：源更新、构建/后端故障时是否仍保持版本、证据和隔离正确
   └──────────────► RQ4：在同一 serving workload 上测延迟、吞吐、内存和 hooks 开销
```

因此，RQ2 产出的 snapshot 是 RQ1/RQ3/RQ4 的共同输入；RQ1 测“回答得好不好”，RQ3 测“生命周期中是否仍然正确”，RQ4 测“系统代价是多少”。旧 report 的 recovery、memory isolation、SQL policy 和单并发 latency 结果都是这条链上的 pilot/diagnostic，不能再作为互相割裂的独立故事。

## 当前状态

| 部分 | 状态 | 还缺什么 |
|---|---|---|
| DataMind 回归 | 已完成：`181 passed, 5 skipped` | 无 |
| RQ1 serving | 待补 | WorkSurface-Bench adapter、gold parser、Route/Evidence scorer、模型 sweep |
| RQ2 build | 待补 | 统一 build driver、六种策略、成本采集和摊平曲线 |
| RQ3 lifecycle | 部分完成 | 统一 source-update/DB/Graph/parser fault runner 和判定器 |
| RQ4 runtime | 部分完成 | 并发 sweep、RSS 采集、no-hooks/full 聚合 |

论文中已经有的旧数字必须标为 pilot，正式投稿前按下面的共同协议重跑。

## 四个 RQ 和表格归属

| RQ | 研究问题 | 直接输入 | 主要结果 | 论文表格 |
|---|---|---|---|---|
| RQ1 | 在固定 published snapshot 上，surface-aware serving 是否提高回答、证据和效率？ | RQ2 的 snapshot + WorkSurface-Bench | Route-F1、Evidence、Answer、Efficiency、tokens、p95 | Table 2--4 |
| RQ2 | 多种 surface 的构建成本是多少，何时由后续查询摊平？ | raw workspace | build time、storage、coverage、provenance、C(N) | Table 5--7 |
| RQ3 | 源更新和组件故障时，系统是否保持 revision、evidence、profile isolation 和安全边界？ | RQ2 的 candidate/published snapshot + 固定 task trace | stale/mixed read、正确 revision、可审计回答、恢复/阻断正确率 | Table 9--12 |
| RQ4 | 管理型 serving path 带来多少延迟、吞吐和内存开销？ | RQ1 的固定 workload 和 snapshot | p50/p95/p99、QPS、RSS、errors、latency breakdown | Table 8 |

DB-GPT/RAGFlow 只属于 RQ1 的 matched-subset 外部基线：DB-GPT 比 database/SQL 子集，RAGFlow 比 document/RAG 子集；不能把它们硬塞进 RQ2--RQ4。

## 统一协议

- **数据链**：固定 workspace、parser 配置、checksum、DataMind commit。RQ2 每次 build 记录 `build_id`、`candidate_revision`、`published_snapshot_id`；RQ1/RQ3/RQ4 显式读取同一 snapshot。
- **模型**：RQ1 按 WorkSurface-Bench 跑 GPT-4o-mini、DeepSeek-V4-Pro、Gemini-3.1-Pro、GPT-5.5；RQ2--RQ4 固定 GPT-5.5 或确定性 workload。锁定 prompt、tool schema、temperature、timeout 和 task order。
- **日志**：每个 task 保存 `rq, condition, task_id, profile_id, snapshot_id, required_surfaces, accessed_surfaces, answer, evidence, revision, tool_calls, invalid_calls, tokens, latency_ms, error`，并保存完整 tool trace。
- **重复**：先用 20 个任务跑通所有条件；主实验全量运行；代表性 200-task 子集重复三次并报告 95% bootstrap CI。未完成 adapter/driver/scorer 前，不把 smoke test 当论文结果。

## RQ1：固定 snapshot 上的 serving 质量

**条件**：No-tool、Always-RAG、Naive-router、ReAct-all、DataMind-full、Gold-constrained（上界）。DataMind-full 使用 manifest/profile/snapshot pinning、evidence 和 fail-closed guard；解析器使用 MinerU API，失败回退 pypdf。

**指标**：Route-F1、Evidence、Answer、Efficiency、tool/irrelevant/invalid calls、tokens、p95 latency。按 RAG、Table、Graph、Cross-surface 分层。

**表格**：Table 2 主结果（模型 × 条件）；Table 3 任务类型；Table 4 DB-GPT/RAGFlow matched subset。RQ1 直接回答“同一个已构建数据版本，DataMind Serving Agent 是否更会选 surface、找证据并完成任务”。

## RQ2：Build Agent 的成本和摊平

所有策略使用相同 raw workspace、parser 和 backend；差别是物化哪些 surface，以及是否有 DataMind 的生命周期管理：

| 策略 | 定义 |
|---|---|
| Document-only / Table-only / Graph-only | 只物化一种 surface，作为成本和能力下界 |
| Eager-all | 一次性物化全部 configured surfaces，但直接写 backend，不做 manifest 驱动的 candidate validation、publication 和 revision 管理 |
| Heuristic-demand | 用预先固定的文件类型/离线 workload 规则选择 surface |
| DataMind-build | Build Agent 物化相同 configured surfaces，并生成 candidate、validation、receipt、published snapshot |

**指标**：build time、API/LLM calls、storage、source coverage、provenance completeness、validation failures；将同一 Worker 放在每个 build 的 published output 上回答固定任务，计算
`C(N)=C_build+N*C_serve`，`N={0,10,50,100,500,1000,5000}`。

**表格**：Table 5 构建成本；Table 6 下游 serving value/摊平；Table 7 旧 MS MARCO chunker/embedder sensitivity，作为 build diagnostic，需重跑后才可作正式结果。

## RQ3：生命周期正确性

对相同 workspace 和相同 serving workload 比较：

- **Direct mutable pipeline**：请求直接读写 live backend，没有 candidate/read guard。
- **DataMind-managed**：candidate validation 后再 publication；请求 pin published snapshot；跨 profile、破坏性 SQL 和 stale provider 由 guard/structured error 阻断。

注入四类事件：source update 与 read/build 重叠、MinerU/parser/embedding 失败、database/SQL timeout/connection/schema failure、Graph unavailable 或 artifact corruption；另测 profile memory leakage 和 destructive SQL policy。

**指标**：completion、正确 revision、stale/mixed-read、auditable-answer、structured-error accuracy、fallback/block correctness、recovery time、memory/answer leakage、unsafe execution。恢复成功必须同时满足答案/任务要求、evidence 可审计、revision 正确；猜到答案不算成功。

**表格**：Table 9 主 fault/update matrix；Table 10 旧 recovery matrix；Table 11 profile isolation；Table 12 SQL policy。它们共同验证“DataMind 管理的 published snapshot 在变化和故障中保持可解释边界”，不是四个独立贡献。

## RQ4：Serving 系统代价

从 RQ1 固定一个 snapshot、task order、model 和 tool schema，只比较：

- **DataMind no-hooks**：保留 serving path，关闭 PathAllowlist、DestructiveSQL、AuditLog hooks。
- **DataMind full**：默认 hooks、evidence、snapshot metadata 和 audit path。
- DB-GPT 只有在模型、数据和任务完全匹配时作为可选参考。

并发度 `1,5,20,50,100`，每条件 60 或 200 tasks，至少三次。报告 errors、p50/p95/p99、QPS、peak RSS、tool/model/hooks latency breakdown、tokens。Table 8 是唯一的 runtime 主表；旧 report 的 concurrency=1 数字标 pilot，补齐 sweep 后替换。

## 执行顺序和分工

1. 共同锁定 workspace、snapshot schema、模型配置和日志 schema；先用 20 tasks 做端到端 smoke。
2. 同学 B 完成 RQ2 build driver，产出可复用 snapshot；同学 A 用该 snapshot 完成 RQ1 adapter/scorer。
3. 同学 D 在同一 snapshot 上完成 RQ3 update/fault runner；同学 C 复用 RQ1 workload 完成 RQ4 runtime sweep。
4. 最后统一生成 Table 2--12 和图，检查每个结果是否能追溯到 `snapshot_id` 和 task-level trace。

每位同学可以独立写自己的 driver 和表格，但不能各自改变 workspace、模型、prompt 或成功判定；共享 runtime 只做向后兼容的最小修改。
