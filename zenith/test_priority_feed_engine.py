"""Unit tests for strict inbox action and UI mapping contracts."""
from agents.inbox_action_engine import InboxActionEngine


def test_task_over_reply_precedence():
    engine = InboxActionEngine()
    email = {
        "id": "email_1",
        "subject": "Can you update API documentation?",
        "from": "Lead",
        "snippet": "Please update it today. Any update?",
    }
    item = engine.build_email_action_item(email)
    assert item["action_type"] == "task"
    assert item["ui_actions"] == ["Add Task", "Edit & Add Task", "Ignore"]
    assert "task_payload" in item
    assert item["task_payload"]["title"].split(" ", 1)[0] in {
        "Update", "Review", "Send", "Prepare", "Draft", "Fix", "Share", "Confirm", "Schedule", "Complete"
    }


def test_meeting_over_task_precedence():
    engine = InboxActionEngine()
    email = {
        "id": "email_2",
        "subject": "Please schedule a meeting and update the plan",
        "from": "Manager",
        "snippet": "Need this done by tomorrow",
    }
    item = engine.build_email_action_item(email)
    assert item["action_type"] == "meeting"
    assert item["ui_actions"] == ["Schedule Meeting", "Edit Details", "Autoprep", "Ignore"]
    assert "meeting_payload" in item
    assert "task_payload" not in item


def test_reply_contract():
    engine = InboxActionEngine()
    email = {
        "id": "email_3",
        "subject": "Need an update?",
        "from": "Rahul",
        "snippet": "Any update on current status?",
    }
    item = engine.build_email_action_item(email)
    assert item["action_type"] == "reply"
    assert item["ui_actions"] == ["Send Reply", "Edit Reply", "Ignore"]
    assert "draft_reply" in item
    assert "meeting_payload" not in item
    assert "task_payload" not in item


def test_ignore_contract():
    engine = InboxActionEngine()
    email = {
        "id": "email_4",
        "subject": "Newsletter weekly digest",
        "from": "News",
        "snippet": "unsubscribe any time",
    }
    item = engine.build_email_action_item(email)
    assert item["action_type"] == "ignore"
    assert item["ui_actions"] == ["Ignore only"]
    assert "draft_reply" not in item
    assert "meeting_payload" not in item
    assert "task_payload" not in item
