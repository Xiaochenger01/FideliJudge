from __future__ import annotations

from app.skills.change_classifier import ChangeClassifier
from app.skills.fact_skill import FactSkill
from app.skills.number_skill import NumberSkill


def test_amount_is_number_not_fact():
    signals = ChangeClassifier().classify_signals("项目金额为1850万元。", "项目金额为1800万元。")
    types = [t for t, _ in signals]
    assert "NUMBER" in types
    assert "FACT" not in types


def test_fact_skill_ignores_shared_words_without_negation():
    assert FactSkill().is_fact_change("项目金额为1850万元", "项目金额为1800万元") is False


def test_extract_chinese_numbers():
    skill = NumberSkill()
    assert skill.extract("合同金额1850万元。") == [(1850.0, "万")]
    assert skill.extract("共有120人参加") == [(120.0, "人")]
    assert skill.extract("增长18.5%") == [(18.5, "%")]
    assert skill.extract("金额 1850 万元") == [(1850.0, "万")]


def test_name_truncation_is_deletion_not_abbreviation():
    ctype, risk = ChangeClassifier().classify_one("负责人：王五", "负责人：")
    assert ctype == "DELETION"
    assert risk == "CRITICAL"


def test_org_suffix_still_term():
    ctype, _ = ChangeClassifier().classify_one("国家电网有限公司", "国家电网")
    assert ctype in {"TERM", "ENTITY"}


def test_person_swap_in_sentence_is_entity():
    ctype, risk = ChangeClassifier().classify_one("张三负责该项目。", "李四负责该项目。")
    assert ctype == "ENTITY"
    assert risk == "HIGH"
