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

旧 report 的数字只有在 workspace、模型、prompt、DataMind commit、故障注入和成功判定都完全一致时才能直接复用；否则保留为 pilot，并用当前协议重跑。Table 7 目前只有 concurrency=1，Table 9--11 使用旧 fault/policy 判定，因此这些已有数字目前属于 pilot，不是因为表格本身有问题，而是为了避免把不可比的数字放在同一主结果中。

## RQ、输入和表格

| RQ | 研究问题 | 输入 | 主要指标 | 论文表格 |
|---|---|---|---|---|
| RQ1 | 在相同 built surfaces 上，surface-aware Serving Agent 是否提高质量和工具效率？ | RQ2 的 built workspace + WorkSurface-Bench | Route-F1、Evidence、Answer、Efficiency、tokens、p95 | Table 2--4 |
| RQ2 | 多种 surface 的构建成本是多少，何时由后续查询摊平？ | raw workspace | build time、storage、coverage、provenance、C(N) | Table 5--6 |
| RQ3 | DataMind Serving Agent 的延迟、吞吐、内存和管理开销是多少？ | RQ1 的固定 task set、built workspace | p50/p95/p99、QPS、RSS、errors、breakdown | Table 7 |
| RQ4 | parser、MinerU、embedding、DB、Graph 等组件异常时，系统能否稳定失败或正确回退？ | 相同 built workspace + 故障注入脚本 | completion、correct answer、structured error、fallback/block、recovery time | Table 8--11 |

DB-GPT 和 RAGFlow 必须参加它们能够支持且协议可对齐的子集：DB-GPT 对 Table/SQL，RAGFlow 对 document/RAG。RQ3 必须报告这些 matched-subset efficiency 结果；RQ4 必须在它们能够复现相同故障的子集上报告 stability 结果。只有不支持的 surface/fault 才填 N/A，并在表注中说明原因。

## 统一协议

- 固定 workspace、文件 checksum、parser 配置、DataMind commit、prompt、tool schema、temperature、timeout 和 task order。
- 每个 build 记录 `build_id`、输入 checksum、物化 surface、耗时、存储和 provenance；每个 task 保存 `rq, condition, task_id, required_surfaces, accessed_surfaces, answer, evidence, tool_calls, invalid_calls, tokens, latency_ms, error`，并保存完整 tool trace。
- 先用 20 个任务跑通所有条件；主实验跑完整任务集；代表性 200-task 子集重复三次并报告 95% bootstrap CI。未完成 adapter/driver/scorer 前，不把 smoke test 写成论文结果。

## RQ1：Serving quality

条件包括 No-tool、Always-RAG、Naive-router、ReAct-all、DataMind-full 和 Gold-constrained（上界）。指标为 Route-F1、Evidence、Answer、Efficiency、tool/irrelevant/invalid calls、tokens 和 p95 latency，并按 RAG、Table、Graph、Cross-surface 分层。

Table 2 是模型 × 条件主结果，Table 3 是任务类型，Table 4 仍使用 WorkSurface-Bench，但只抽取可公平复现的 matched subset：DB-GPT 对 Table/SQL，RAGFlow 对 document/RAG。三者使用相同 task id、workspace、问题、模型和输出预算；RQ1 只研究问答质量和调用效率，不把故障处理混入主分数。

### Table 2–4：RQ1 serving quality

这张表回答 RQ1 的主问题：在相同任务和 built workspace 上，DataMind-full 是否比 ReAct-all 提高路由、证据、答案和工具效率。横向比较不同模型，纵向比较两种 serving 条件；若 Answer 提升同时 Tokens/p95 降低，说明收益来自 surface-aware serving，而不是单纯模型差异。

**Table 2 — 主结果（每个模型至少 ReAct-all/DataMind-full）**

| Model | Condition | Route-F1↑ | Evidence↑ | Answer↑ | Efficiency↑ | Tokens↓ | p95 ms↓ |
|---|---|---:|---:|---:|---:|---:|---:|
| GPT-4o-mini | ReAct-all | TBD | TBD | TBD | TBD | TBD | TBD |
| GPT-4o-mini | DataMind-full | TBD | TBD | TBD | TBD | TBD | TBD |
| DeepSeek-V4-Pro | ReAct-all | TBD | TBD | TBD | TBD | TBD | TBD |
| DeepSeek-V4-Pro | DataMind-full | TBD | TBD | TBD | TBD | TBD | TBD |
| Gemini-3.1-Pro | ReAct-all | TBD | TBD | TBD | TBD | TBD | TBD |
| Gemini-3.1-Pro | DataMind-full | TBD | TBD | TBD | TBD | TBD | TBD |
| GPT-5.5 | ReAct-all | TBD | TBD | TBD | TBD | TBD | TBD |
| GPT-5.5 | DataMind-full | TBD | TBD | TBD | TBD | TBD | TBD |

这张表检查 RQ1 的收益来自哪类 surface。它比较 ReAct-all、Naive-router、DataMind-full 和 Gold-hint/all 在 RAG、Table、Graph、Cross-surface 任务上的表现，用来判断 DataMind 是否真正解决跨 surface 路由，而不是只在文档问答上获益。

**Table 3 — 按任务类型**

| Condition | RAG Answer | Table Answer | Graph Answer | Cross Answer | Evidence |
|---|---:|---:|---:|---:|---:|
| ReAct-all | TBD | TBD | TBD | TBD | TBD |
| Naive-router | TBD | TBD | TBD | TBD | TBD |
| DataMind-full | TBD | TBD | TBD | TBD | TBD |
| Gold-hint/all | TBD | TBD | TBD | TBD | TBD |

这张表把 DataMind 与已有系统放在它们真正支持的任务子集上比较：DB-GPT 对 Table/SQL，RAGFlow 对 RAG/document。它说明 DataMind 的优势是否超出内部 baseline；不同系统不支持的任务不填 0，而填 N/A。

**Table 4 — WorkSurface-Bench matched subset 外部比较**

| System | Subset | Route-F1 | Evidence | Answer | p95 ms | Errors |
|---|---|---:|---:|---:|---:|---:|
| DB-GPT | Table/SQL | TBD | TBD | TBD | TBD | TBD |
| RAGFlow | RAG/document | TBD | TBD | TBD | TBD | TBD |
| DataMind-full | Same subset | TBD | TBD | TBD | TBD | TBD |

## RQ2：Build Agent 成本和摊平

所有策略使用相同 raw workspace、parser 和 backend：

| 策略 | 定义 |
|---|---|
| Document-only / Table-only / Graph-only | 只物化一种 surface，作为成本和能力下界 |
| Eager-all | 一次性物化全部 configured surfaces，直接写 backend，不额外引入 DataMind 的编排路径 |
| Heuristic-demand | 按预先固定的文件类型或离线 workload 规则选择 surface |
| DataMind-build | 使用 DataMind Build Agent 物化 configured surfaces，并记录完整 provenance、validation 和构建结果 |

记录 build time、API/LLM calls、storage、source coverage、provenance completeness、validation failures；让同一个 Worker 在各策略产物上回答固定任务，计算 `C(N)=C_build+N*C_serve`，`N={0,10,50,100,500,1000,5000}`。Table 5 和 Table 6 共同覆盖构建成本、下游价值和摊平分析。

### Table 5–6：RQ2 build cost

这张表回答 RQ2 的第一部分：构建不同 surface 需要多少时间、调用、存储和验证成本，以及覆盖率和 provenance 是否完整。比较单 surface、Eager-all、Heuristic-demand 与 DataMind-build，用来说明 DataMind 的入库代价及其数据质量。

**Table 5 — 构建成本和覆盖率**

| Strategy | Time s↓ | API calls↓ | Storage MB↓ | Coverage↑ | Provenance↑ | Validation failures↓ |
|---|---:|---:|---:|---:|---:|---:|
| Document-only | TBD | TBD | TBD | TBD | TBD | TBD |
| Table-only | TBD | TBD | TBD | TBD | TBD | TBD |
| Graph-only | TBD | TBD | TBD | TBD | TBD | TBD |
| Eager-all | TBD | TBD | TBD | TBD | TBD | TBD |
| Heuristic-demand | TBD | TBD | TBD | TBD | TBD | TBD |
| DataMind-build | TBD | TBD | TBD | TBD | TBD | TBD |

这张表回答 RQ2 的第二部分：不同构建策略产生的数据，是否真的改善后续 Serving。所有策略由同一个 Worker 在相同任务上回答；Answer/Evidence/Efficiency 与 Cost/query 一起决定多 surface 构建是否值得。

**Table 6 — 构建后的 serving value**

| Strategy | N | Answer | Evidence | Efficiency | p95 ms | Cost/query |
|---|---:|---:|---:|---:|---:|---:|
| Document-only | 100 | TBD | TBD | TBD | TBD | TBD |
| Eager-all | 100 | TBD | TBD | TBD | TBD | TBD |
| DataMind-build | 100 | TBD | TBD | TBD | TBD | TBD |

## RQ3：Serving efficiency

固定 RQ1 的 task set、模型、prompt、tool schema 和 built workspace，只比较：

- **DataMind no-hooks**：保留完整 serving path，关闭 PathAllowlist、DestructiveSQL 和 AuditLog hooks；
- **DataMind full**：默认配置，启用 hooks、evidence 和审计路径；
- **DB-GPT/RAGFlow（matched subset，必须）**：DB-GPT 对 Table/SQL，RAGFlow 对 RAG/document；协议不支持的单元格填 N/A。

并发度为 `1,5,20,50,100`，每条件 60 或 200 tasks，至少三次。DataMind、DB-GPT 和 RAGFlow 在各自 matched subset 上使用相同的 concurrency、N、task order、模型 endpoint、timeout、硬件和 warm-up；不能满足这些条件的系统只报告单独 latency，不做直接 QPS 比较。报告 errors、p50/p95/p99、QPS、peak RSS、tool/model/hooks latency breakdown 和 tokens。Table 7 是 runtime 主表；旧单并发数字只作 pilot。

### Table 7：RQ3 serving efficiency

这张表回答 RQ3：DataMind 的 serving 管理路径带来多少系统开销。比较 no-hooks、full 和匹配的外部系统，在相同任务集上观察并发升高时的延迟、QPS、RSS 和错误率；它不衡量答案质量。

**Table 7 — 并发、延迟、吞吐和内存**

| System | Concurrency | N | Errors↓ | p50 ms↓ | p95 ms↓ | p99 ms↓ | QPS↑ | Peak RSS MB↓ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DataMind no-hooks | 1 | 60 | 2 | 9373.8 | 18329.4 | 24302.7 | 0.0917 | 193.5 |
| DataMind full | 1 | 60 | 2 | 8458.0 | 15413.4 | 19560.0 | 0.1012 | 188.1 |
| DataMind no-hooks | 20 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| DataMind full | 20 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| DataMind no-hooks | 100 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| DataMind full | 100 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| DB-GPT (matched Table/SQL) | 1 | 60 | 0 | 7164.1 | 11660.2 | 13839.5 | 0.1297 | 194.0 |
| RAGFlow (matched RAG) | 1 | 60 | TBD | TBD | TBD | TBD | TBD | TBD |

## RQ4：组件故障下的稳定性

在相同 built workspace 和确定性 task set 上注入：MinerU/parser timeout、embedding outage、empty retrieval、DB/SQL timeout、connection/schema failure、Graph unavailable、artifact corruption 和 interrupted build。每个故障都要有预先定义的期望行为：fallback、structured error、block 或 retry。

比较 DataMind、retry-only/direct baseline，以及在对应子集上强制加入的 DB-GPT（Table/SQL）和 RAGFlow（document/RAG）。指标为 completion、correct answer、auditable evidence、structured-error accuracy、fallback/block correctness、recovery time、unsafe answer/execution rate。恢复成功必须同时满足任务要求和证据有效；猜对答案不算稳定恢复。

Table 8 是统一 fault matrix；Table 9 是旧 recovery pilot；Table 10 是 profile/memory isolation；Table 11 是 SQL policy safety。四张表共同回答“组件异常时系统是否保持可控行为”，不再拆成多个互不相关的贡献。

### Table 8–11：RQ4 component stability

这张表回答 RQ4 的核心问题：组件挂掉时，系统是否按预期 fallback、retry、structured error 或 block。每种事件比较 Direct mutable、DataMind-full 以及可匹配的 DB-GPT/RAGFlow，结果用于区分“稳定失败”与“返回错误答案”。

**Table 8 — 统一故障矩阵**

| Event | System | Completion | Answer | Auditable | Structured error | Fallback/block | Recovery ms |
|---|---|---:|---:|---:|---:|---:|---:|
| Parser/MinerU failure | Direct mutable | TBD | TBD | TBD | TBD | TBD | TBD |
| Parser/MinerU failure | DataMind-full | TBD | TBD | TBD | TBD | TBD | TBD |
| Parser/MinerU failure | RAGFlow (matched RAG) | TBD | TBD | TBD | TBD | TBD | TBD |
| Database/SQL timeout | Direct mutable | TBD | TBD | TBD | TBD | TBD | TBD |
| Database/SQL timeout | DataMind-full | TBD | TBD | TBD | TBD | TBD | TBD |
| Database/SQL timeout | DB-GPT (matched Table/SQL) | TBD | TBD | TBD | TBD | TBD | TBD |
| Graph unavailable | Direct mutable | TBD | TBD | TBD | TBD | TBD | TBD |
| Graph unavailable | DataMind-full | TBD | TBD | TBD | TBD | TBD | TBD |

这张表保留旧 report 的总体 recovery 结果，作为 RQ4 的历史 pilot。它比较 Fixed pipeline 与 DataMind live 在 KB、Graph、DB 和 corruption 故障下的恢复率；正式结果必须用当前的 evidence 和正确性判定重跑。

**Table 9 — 旧 report recovery pilot（按新判定重跑）**

| System | KB empty | Graph down | DB timeout | Partial corruption | Overall |
|---|---:|---:|---:|---:|---:|
| Fixed pipeline | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) | 0.0% (0) |
| DataMind live | 60.0% (3) | 60.7% (17) | 70.6% (12) | 62.5% (25) | 63.3% (57) |

这张表验证 RQ4 的隔离稳定性。比较 Flat namespace 与 DataMind three-scope 的记忆泄漏、答案泄漏和召回率；理想结果是泄漏为 0、合法记忆召回为 100%。

**Table 10 — profile/memory isolation**

| Setting | Memory leakage↓ | Memory recall↑ | Answer leakage↓ | Answer recall↑ | Mixed answer↓ |
|---|---:|---:|---:|---:|---:|
| Flat namespace | 30% | 70% | 68% | 31% | 63% |
| DataMind three-scope | 0% | 100% | 0% | 100% | 0% |

这张表验证 RQ4 的 SQL 安全边界。比较直接执行、关键词 guard、DB-GPT 和 DataMind hooks 对危险 SQL 的召回与误报，说明系统能否拦住危险操作而不过度阻断安全查询。

**Table 11 — SQL policy safety**

| System | Unsafe recall↑ | FP rate↓ | Recall--FP↑ |
|---|---:|---:|---:|
| Direct execution | 0% | 0% | 0% |
| Keyword guard | 8% | 0% | 8% |
| DB-GPT | 82% | 56% | 26% |
| DataMind hooks | 100% | 0% | 100% |

验收时先确认每张表的 adapter/driver 能生成一行真实 JSON，再填整表；不要直接手工修改论文中的 `TBD`。

## 执行顺序和分工

1. 共同锁定 workspace、模型、prompt、日志 schema 和成功判定，先用 20 tasks 做 smoke。
2. 同学 B 完成 RQ2 build driver；同学 A 在相同 built workspace 上完成 RQ1 adapter/scorer。
3. 同学 C 复用 RQ1 task set 完成 RQ3 efficiency；同学 D 在相同 workspace 上完成 RQ4 fault runner。
4. 统一生成 Table 2--11 和图，检查每个结果都能追溯到 build、task id 和完整 trace。

同学可以分别写 driver 和填表，但不能各自改变数据、模型、prompt 或成功判定；共享 runtime 只做向后兼容的最小修改。
