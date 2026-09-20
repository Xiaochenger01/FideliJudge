# 保真判 · FideliJudge

**面向数据治理的语义保真度评估智能体。**

A semantic-fidelity judge for data-governance pipelines.

它不修改业务数据，只回答一件事：治理后的文本，是否仍然保住了治理前的语义与事实。

输出 `AUTO_PASS` / `REVIEW` / `REJECT`，并留下可定位、可解释、可回放的审计 Trace。

[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI](https://img.shields.io/badge/tests-28%20passed-brightgreen)](.github/workflows/ci.yml)

---

## 为什么不是「算个相似度」

数据治理流水线会清洗、归一、修复文本。格式变干净了，不等于内容还对。

长文档里改一个金额，字面相似度仍然很高——这正是本项目要拦住的情况。

| 治理前 | 治理后 | 判定 |
|--------|--------|------|
| 国家电网有限公司 | 国家电网 | 合理简称 → 可过 |
| 2025年6月11日 | 2025年 | 时间粒度损失 → 审核 |
| 1850万元 | 1800万元 | 核心数值改写 → 拒绝 |
| 已完成验收 | 正在验收 | 事实状态翻转 → 拒绝 |

```text
Diff → 变化分类 → 规则 Skill → Judge → 评分 → 路由 → SQLite
```

规则保底线，LLM 只理解/解释，**最终路由由配置决定**。

---

## 快速开始

无需 API Key。默认 Mock Judge，结果可复现。

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python scripts/build_dataset.py
uvicorn app.main:app --reload --port 8000
```

打开 http://127.0.0.1:8000 ，API 文档在 `/docs`。

切换真实模型（OpenAI 兼容，含 DeepSeek / 本地 vLLM）：

```bash
export FIDELI_LLM_PROVIDER=openai_compat
export FIDELI_LLM_API_KEY=sk-...
export FIDELI_LLM_BASE_URL=https://api.deepseek.com/v1
export FIDELI_LLM_MODEL=deepseek-flash
```

Docker：`docker compose up --build`

---

## 评测（可复现 Mock Benchmark）

本轮默认是 **mock（规则 + 确定性 Judge）**，不是「假装跑了大模型」。
`config/model.yaml` 的 `provider` 为 `mock`。无 Key 时即使写成 `openai_compat` 也会显式回退。

```bash
python scripts/run_eval.py
python scripts/run_human_agreement.py
python scripts/stability_test.py 5
pytest -q
```

54 条自建集（`evaluation/reports/latest.json`，2026-09-12，provider=mock）：

| 方法 | Accuracy | Unsafe F1 |
|------|----------|-----------|
| **FideliJudge** | **0.907** | **0.928** |
| 去掉 Diff 锚点（消融） | 0.852 | 0.889 |
| 字面相似度 | 0.611 | 0.687 |
| char n-gram TF-IDF | 0.611 | 0.712 |

Unsafe recall = 1.0；定位覆盖约 0.98。长文改金额/事实时，相似度基线会放行，本管道会拦。

**数字边界（面试会问）：**

- 以上是规则 + 确定性 Judge，接真实 LLM 需重跑并另存报告。
- `human_labels.jsonl` 的 author_v1 与金标同源，三分类 κ=0.58 只能作自检；独立标注用 `datasets/peer_annotation_template.jsonl`。
- mock + temperature=0 的 std=0 **不能**当作 LLM 稳定性。

---

## 架构

设计说明：[docs/design.md](docs/design.md)

```text
POST /api/v1/evaluations
        │
        ▼
  DiffSkill          句子级对齐，字符锚点，不调用 LLM
        │
  ChangeClassifier   FORMAT / TIME / NUMBER / TERM / ENTITY / FACT / ...
        │
  Rule Skills        时间粒度、数值严重度、机构简称、事实极性
        │
  SemanticJudge      Mock 或 OpenAI 兼容；FORMAT/STRUCTURE 跳过 LLM
        │
  FidelityScorer     结构/实体/数值/时间/事实 加权 + CRITICAL 惩罚
        │
  RoutingEngine      AUTO_PASS / REVIEW / REJECT
        │
  SQLite Trace       task → stages → issues → 可回放
```

路由契约（`config/routing.yaml`）：

```text
CRITICAL 或 score < 60     → REJECT
HIGH 或 score < 85         → REVIEW
否则且无高风险             → AUTO_PASS
```

核心 API：`POST /evaluations` · `GET /{id}` · `/result` · `/issues` · `/trace`

---

## 目录

```text
app/
  agents/          FidelityAgent · SemanticJudge
  skills/          diff · classifier · time · number · entity · fact
  evaluators/      scorer · calibration（Cohen's κ）
  routing/         YAML 阈值 + 一票否决
  llm/             mock · openai_compat
  api/ storage/    FastAPI + SQLite
config/            routing.yaml · scoring.yaml · model.yaml
prompts/           Judge prompt，与代码分离
datasets/          evaluation.jsonl（54 条）
evaluation/        基线 · 已提交的 mock 报告
frontend/          单页 Demo
tests/             单元 + 集成
```

---

## 状态

**Phase 1 / v0.1 已完成：** MVP 闭环、句子级 Diff、评测消融、人工一致性脚本、稳定性脚本（区分 mock / LLM）、pytest CI。



## License

MIT
