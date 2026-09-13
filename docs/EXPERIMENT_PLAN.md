# DataMind SIGMOD 实验计划

实验按 DataMind 的实际工作流串成一条线：入库、问答、效率、稳定性。
RQ1 和 RQ2 关注“能不能做好、构建是否值得”；RQ3 和 RQ4 关注“跑得是否快、组件异常时是否可靠”。每个 RQ 可以由不同同学实现，但必须使用相同 workspace、模型配置、问题集和日志格式。

```text
Raw workspace ──► RQ2 Build Agent ──► built surfaces
                                        │
                                        ├──► RQ1 Serving quality
                                        ├──► RQ3 Serving efficiency
                                        └──► RQ4 Fault stability
```

## 当前状态

| 部分 | 状态 | 还缺什么 |
|---|---|---|
| DataMind 回归 | 已完成：`181 passed, 5 skipped` | 无 |
| RQ1 serving quality | 待补 | WorkSurface-Bench adapter、gold parser、scorer、模型 sweep |
| RQ2 build cost | 待补 | 统一 build driver、策略实现、成本采集和摊平曲线 |
| RQ3 efficiency | 部分完成 | 并发 sweep、RSS 采集、no-hooks/full 聚合、外部基线匹配 |
| RQ4 stability | 部分完成 | parser/MinerU、DB、Graph、embedding 故障注入和统一判定器 |

旧 report 的数字统一标为 pilot，正式投稿前按同一协议复现。

## RQ、输入和表格

| RQ | 研究问题 | 输入 | 主要指标 | 论文表格 |
|---|---|---|---|---|
| RQ1 | 在相同 built surfaces 上，surface-aware Serving Agent 是否提高质量和工具效率？ | RQ2 的 built workspace + WorkSurface-Bench | Route-F1、Evidence、Answer、Efficiency、tokens、p95 | Table 2--4 |
| RQ2 | 多种 surface 的构建成本是多少，何时由后续查询摊平？ | raw workspace | build time、storage、coverage、provenance、C(N) | Table 5--7 |
| RQ3 | DataMind Serving Agent 的延迟、吞吐、内存和管理开销是多少？ | RQ1 的固定 task set、built workspace | p50/p95/p99、QPS、RSS、errors、breakdown | Table 8 |
| RQ4 | parser、MinerU、embedding、DB、Graph 等组件异常时，系统能否稳定失败或正确回退？ | 相同 built workspace + 故障注入脚本 | completion、correct answer、structured error、fallback/block、recovery time | Table 9--12 |

DB-GPT 和 RAGFlow 不只用于 RQ1：在能对齐模型、数据、问题、输出预算的子集上，它们也可以作为 RQ3 的效率基线和 RQ4 的稳定性基线。无法对齐时只报告定性能力，不填定量数字。

## 统一协议

- 固定 workspace、文件 checksum、parser 配置、DataMind commit、prompt、tool schema、temperature、timeout 和 task order。
- 每个 build 记录 `build_id`、输入 checksum、物化 surface、耗时、存储和 provenance；每个 task 保存 `rq, condition, task_id, required_surfaces, accessed_surfaces, answer, evidence, tool_calls, invalid_calls, tokens, latency_ms, error`，并保存完整 tool trace。
- 先用 20 个任务跑通所有条件；主实验跑完整任务集；代表性 200-task 子集重复三次并报告 95% bootstrap CI。未完成 adapter/driver/scorer 前，不把 smoke test 写成论文结果。

## RQ1：Serving quality

条件包括 No-tool、Always-RAG、Naive-router、ReAct-all、DataMind-full 和 Gold-constrained（上界）。指标为 Route-F1、Evidence、Answer、Efficiency、tool/irrelevant/invalid calls、tokens 和 p95 latency，并按 RAG、Table、Graph、Cross-surface 分层。

Table 2 是模型 × 条件主结果，Table 3 是任务类型，Table 4 是 matched-subset 外部系统：DB-GPT 对 Table/SQL，RAGFlow 对 document/RAG。RQ1 只研究问答质量和调用效率，不把故障处理混入主分数。

## RQ2：Build Agent 成本和摊平

所有策略使用相同 raw workspace、parser 和 backend：

| 策略 | 定义 |
|---|---|
| Document-only / Table-only / Graph-only | 只物化一种 surface，作为成本和能力下界 |
| Eager-all | 一次性物化全部 configured surfaces，直接写 backend，不额外引入 DataMind 的编排路径 |
| Heuristic-demand | 按预先固定的文件类型或离线 workload 规则选择 surface |
| DataMind-build | 使用 DataMind Build Agent 物化 configured surfaces，并记录完整 provenance、validation 和构建结果 |

记录 build time、API/LLM calls、storage、source coverage、provenance completeness、validation failures；让同一个 Worker 在各策略产物上回答固定任务，计算 `C(N)=C_build+N*C_serve`，`N={0,10,50,100,500,1000,5000}`。Table 7 的旧 MS MARCO chunker/embedder 数字是 build diagnostic，需重跑。

## RQ3：Serving efficiency

固定 RQ1 的 task set、模型、prompt、tool schema 和 built workspace，只比较：

- **DataMind no-hooks**：保留完整 serving path，关闭 PathAllowlist、DestructiveSQL 和 AuditLog hooks；
- **DataMind full**：默认配置，启用 hooks、evidence 和审计路径；
- **DB-GPT/RAGFlow（可选）**：仅在模型、数据、问题和输出协议完全匹配时加入。

并发度为 `1,5,20,50,100`，每条件 60 或 200 tasks，至少三次。报告 errors、p50/p95/p99、QPS、peak RSS、tool/model/hooks latency breakdown 和 tokens。Table 8 是 runtime 主表；旧单并发数字只作 pilot。

## RQ4：组件故障下的稳定性

在相同 built workspace 和确定性 task set 上注入：MinerU/parser timeout、embedding outage、empty retrieval、DB/SQL timeout、connection/schema failure、Graph unavailable、artifact corruption 和 interrupted build。每个故障都要有预先定义的期望行为：fallback、structured error、block 或 retry。

比较 DataMind、retry-only/direct baseline，以及能完全对齐时的 DB-GPT/RAGFlow。指标为 completion、correct answer、auditable evidence、structured-error accuracy、fallback/block correctness、recovery time、unsafe answer/execution rate。恢复成功必须同时满足任务要求和证据有效；猜对答案不算稳定恢复。

Table 9 是统一 fault matrix；Table 10 是旧 recovery pilot；Table 11 是 profile/memory isolation；Table 12 是 SQL policy safety。四张表共同回答“组件异常时系统是否保持可控行为”，不再拆成多个互不相关的贡献。

## 执行顺序和分工

1. 共同锁定 workspace、模型、prompt、日志 schema 和成功判定，先用 20 tasks 做 smoke。
2. 同学 B 完成 RQ2 build driver；同学 A 在相同 built workspace 上完成 RQ1 adapter/scorer。
3. 同学 C 复用 RQ1 task set 完成 RQ3 efficiency；同学 D 在相同 workspace 上完成 RQ4 fault runner。
4. 统一生成 Table 2--12 和图，检查每个结果都能追溯到 build、task id 和完整 trace。

同学可以分别写 driver 和填表，但不能各自改变数据、模型、prompt 或成功判定；共享 runtime 只做向后兼容的最小修改。
