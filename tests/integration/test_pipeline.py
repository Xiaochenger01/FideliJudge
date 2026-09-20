from __future__ import annotations

from app.agents.fidelity_agent import FidelityAgent


def test_demo_case_rejects_or_reviews(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    monkeypatch.setenv("FIDELI_DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("FIDELI_LLM_PROVIDER", "mock")
    monkeypatch.delenv("FIDELI_LLM_API_KEY", raising=False)
    from app.core.config import get_settings
    get_settings.cache_clear()

    agent = FidelityAgent()
    before = "项目于2025年6月11日完成验收，项目金额为1850万元。"
    after = "项目于2025年完成验收，项目金额为1800万元。"
    out = agent.evaluate(before, after)
    result = out["result"]
    assert result.route in {"REVIEW", "REJECT"}
    assert result.risk_level in {"HIGH", "CRITICAL"}
    assert result.overall_score < 85
    types = {c.change_type for c in result.changes}
    assert "TIME" in types or "NUMBER" in types or any(
        i.change_type in {"TIME", "NUMBER"} for i in result.issues
    )


def test_fact_flip_must_not_auto_pass(tmp_path, monkeypatch):
    db = tmp_path / "t3.db"
    monkeypatch.setenv("FIDELI_DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("FIDELI_LLM_PROVIDER", "mock")
    monkeypatch.delenv("FIDELI_LLM_API_KEY", raising=False)
    from app.core.config import get_settings
    get_settings.cache_clear()

    agent = FidelityAgent()
    out = agent.evaluate("审批已通过", "审批未通过")
    result = out["result"]
    assert result.route != "AUTO_PASS"
    assert result.risk_level in {"HIGH", "CRITICAL"}
    assert any(i.change_type == "FACT" for i in result.issues) or any(
        c.change_type == "FACT" for c in result.changes
    )


def test_abbreviation_can_pass(tmp_path, monkeypatch):
    db = tmp_path / "t2.db"
    monkeypatch.setenv("FIDELI_DATABASE_URL", f"sqlite:///{db}")
    monkeypatch.setenv("FIDELI_LLM_PROVIDER", "mock")
    monkeypatch.delenv("FIDELI_LLM_API_KEY", raising=False)
    from app.core.config import get_settings
    get_settings.cache_clear()

    agent = FidelityAgent()
    out = agent.evaluate("国家电网有限公司发布通知。", "国家电网发布通知。")
    result = out["result"]
    assert result.route in {"AUTO_PASS", "REVIEW"}
    assert result.overall_score >= 70
