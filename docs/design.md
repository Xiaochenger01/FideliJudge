# FideliJudge 设计说明（公开版）

> Phase 1 / v0.1 — 语义保真评估 MVP + 可复现评测骨架

## 一句话

数据治理会把文本洗干净。保真判站在流水线出口，判断**治理后是否仍保住治理前的语义与事实**。它不改业务数据。

## 原则

1. **规则优先**：格式 Diff、时间粒度、数值改写、事实极性不依赖 LLM。
2. **LLM 只判断，系统做路由**：阈值与 CRITICAL 一票否决写在 `config/routing.yaml`。
3. **结论可回放**：每次评估留下 Task / Trace / Skill / Model / Prompt 版本。
4. **配置外置**：权重、阈值、模型、Skill 开关不写死在业务代码里。
5. **Evaluate ≠ Transform**：只评估，禁止改写治理结果。

## 管道

```text
API → DiffSkill → ChangeClassifier → Time/Number/Entity/Fact
    → SemanticJudge → FidelityScorer → RoutingEngine → SQLite Trace
```

| 模块 | 职责 |
|------|------|
| DiffSkill | 句子级对齐 + 字符锚点，不调用 LLM |
| ChangeClassifier | FORMAT / TIME / NUMBER / TERM / ENTITY / FACT / DELETION / ADDITION / UNKNOWN |
| SemanticJudge | 结构化 JSON；Mock 或 OpenAI 兼容接口 |
| FidelityScorer | 五维加权 + 高风险惩罚 |
| Router | `AUTO_PASS` / `REVIEW` / `REJECT` |

## 路由契约

```text
CRITICAL 或 score < review          → REJECT
HIGH 或 score < auto_pass           → REVIEW
低置信度（真实 LLM）                 → REVIEW
否则且无 HIGH/CRITICAL              → AUTO_PASS
```

无 API Key 时显式回退 Mock，**不会**把 mock 结果一律打成 REVIEW。

## 评测口径

- 默认报告是 **mock（规则 + 确定性 Judge）**，不是真实大模型分数。
- `datasets/human_labels.jsonl` 的 author_v1 与金标同源，κ 只能作自检。
- mock + temperature=0 的 std=0 **不能**当作 LLM 稳定性。

完整数字见 `evaluation/reports/latest.json`。

## Phase 1 范围

**做了：** FastAPI 闭环、句子级 Diff、规则 Skill、可插拔 Judge、评分与路由、SQLite Trace、Demo 前端、54 条评测集、基线与消融、pytest。

**刻意没做：** 大规模独立标注、真实 LLM 对比实验、多智能体 / RAG / 微调、复杂前端。
