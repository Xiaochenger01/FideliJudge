from __future__ import annotations

from app.skills.change_classifier import ChangeClassifier
from app.skills.diff_skill import DiffSkill


def test_diff_finds_time_and_number_fragments():
    before = "项目于2025年6月11日完成验收，项目金额为1850万元。"
    after = "项目于2025年完成验收，项目金额为1800万元。"
    changes = DiffSkill().diff_texts(before, after)
    assert len(changes) >= 1
    joined_b = "".join(c.before_text for c in changes)
    joined_a = "".join(c.after_text for c in changes)
    blob = joined_b + joined_a
    assert any(token in blob for token in ("6月", "11日", "1850", "1800", "5", "0"))
    assert joined_b != joined_a or any(c.before_text != c.after_text for c in changes)


def test_sentence_diff_keeps_fact_words():
    changes = DiffSkill().diff_texts("审批已通过", "审批未通过")
    assert len(changes) == 1
    assert "通过" in changes[0].before_text
    assert "通过" in changes[0].after_text
    assert "已" in changes[0].before_text
    assert "未" in changes[0].after_text


def test_classifier_time():
    ctype, risk = ChangeClassifier().classify_one("2025年6月", "2025年")
    assert ctype == "TIME"
    assert risk in {"HIGH", "MEDIUM"}


def test_classifier_number():
    ctype, risk = ChangeClassifier().classify_one("1850万元", "1800万元")
    assert ctype == "NUMBER"
    assert risk in {"HIGH", "CRITICAL"}


def test_classifier_term():
    ctype, risk = ChangeClassifier().classify_one("国家电网有限公司", "国家电网")
    assert ctype in {"TERM", "ENTITY"}


def test_classifier_fact():
    ctype, risk = ChangeClassifier().classify_one("已完成验收", "正在验收")
    assert ctype == "FACT"
    assert risk == "CRITICAL"


def test_classifier_fact_negation_flip():
    ctype, risk = ChangeClassifier().classify_one("审批已通过", "审批未通过")
    assert ctype == "FACT"
    assert risk == "CRITICAL"


def test_punct_deletion_is_format_not_deletion():
    ctype, risk = ChangeClassifier().classify_one("项目，于今日启动。", "项目于今日启动。")
    assert ctype == "FORMAT"
    assert risk == "LOW"


def test_punct_addition_is_format():
    ctype, risk = ChangeClassifier().classify_one("附件见附录A", "附件见附录A。")
    assert ctype == "FORMAT"


def test_adjacent_sentences_get_two_anchors():
    before = "国家电网有限公司承建。合同金额1850万元。"
    after = "国家电网承建。合同金额1800万元。"
    changes = DiffSkill().diff_texts(before, after)
    assert len(changes) >= 2
    joined_b = "".join(c.before_text for c in changes)
    assert "有限公司" in joined_b
    assert "1850" in joined_b
    spans = [(c.position_before.start, c.position_before.end) for c in changes]
    assert len(set(spans)) >= 2
