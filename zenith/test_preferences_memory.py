"""Tests for conversational memory extraction and fast intent classification."""
from agents.context_agent import ContextAgent
from memory.preferences import PreferencesStore


def test_extract_memory_updates_dislikes_multiple_items():
    updates = PreferencesStore.extract_memory_updates_from_text(
        "I don't like strawberry and pineapple."
    )

    assert updates["dislikes"] == ["strawberry", "pineapple"]
    assert updates["likes"] == []


def test_extract_memory_updates_preference_phrase():
    updates = PreferencesStore.extract_memory_updates_from_text(
        "I prefer email over calls."
    )

    assert updates["preferences"] == ["email over calls"]


def test_build_prompt_context_includes_memory_profile():
    prompt_context = PreferencesStore.build_prompt_context(
        {
            "email_tone": "casual",
            "custom_rules": ["Keep answers short"],
            "memory_profile": {
                "dislikes": ["strawberry"],
                "preferences": ["email over calls"],
            },
        }
    )

    assert "Email tone: casual" in prompt_context
    assert "Keep answers short" in prompt_context
    assert "strawberry" in prompt_context
    assert "email over calls" in prompt_context


def test_quick_classifier_marks_preference_updates_as_conversation():
    agent = ContextAgent.__new__(ContextAgent)
    intent = ContextAgent._quick_classify_intent(agent, "I don't like strawberry")

    assert intent["category"] == "A"
    assert intent["intent"] == "preference_update"


def test_quick_classifier_detects_email_work():
    agent = ContextAgent.__new__(ContextAgent)
    intent = ContextAgent._quick_classify_intent(agent, "Summarize my unread emails")

    assert intent["category"] == "B"
    assert intent["intent"] == "summarize_inbox"
    assert intent["requires_tools"] == ["gmail"]
