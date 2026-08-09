from __future__ import annotations

from pathlib import Path

from voice_agent.knowledge import MarkdownKnowledgeBase

ROOT = Path(__file__).resolve().parents[1]


def test_matches_breakfast_policy() -> None:
    knowledge = MarkdownKnowledgeBase.from_directory(ROOT / "knowledge")
    result = knowledge.search("What time is breakfast served?")

    assert result is not None
    assert result.source_id == "policy.breakfast"
    assert "6:30 AM" in result.answer


def test_matches_chinese_breakfast_question() -> None:
    knowledge = MarkdownKnowledgeBase.from_directory(ROOT / "knowledge")
    result = knowledge.search("早餐时间是什么?")

    assert result is not None
    assert result.source_id == "policy.breakfast"


def test_unknown_question_returns_no_match() -> None:
    knowledge = MarkdownKnowledgeBase.from_directory(ROOT / "knowledge")

    assert knowledge.search("Who designed the painting in the lobby?") is None


def test_all_knowledge_sources_are_unique() -> None:
    knowledge = MarkdownKnowledgeBase.from_directory(ROOT / "knowledge")
    source_ids = [document.source_id for document in knowledge.documents]

    assert len(source_ids) == len(set(source_ids))
