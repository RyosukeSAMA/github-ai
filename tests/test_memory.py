from __future__ import annotations

from pantheon.core.memory import MemoryStore, detect_memory_candidate


def test_memory_store_add_search_and_delete(tmp_path) -> None:
    store = MemoryStore(tmp_path / ".pantheon" / "memory.sqlite")

    item = store.add(
        "User prefers concise Chinese answers for Pantheon UI work.",
        kind="user_profile",
        source="manual",
        role="athena",
        tags=["ui"],
    )

    assert item["kind"] == "user_profile"
    assert item["source"] == "manual"
    assert item["role"] == "athena"
    assert store.stats()["count"] == 1

    matches = store.search("Chinese Pantheon UI", role="athena")
    assert [match["id"] for match in matches] == [item["id"]]

    context, context_items = store.context_block("Pantheon UI Chinese", role="athena")
    assert "Relevant long-term memories" in context
    assert context_items[0]["id"] == item["id"]

    assert store.delete(item["id"]) is True
    assert store.list() == []


def test_memory_store_settings_and_clear(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")

    assert store.settings() == {"enabled": True, "auto_capture": False}
    assert store.set_settings(enabled=False, auto_capture=True) == {
        "enabled": False,
        "auto_capture": True,
    }

    store.add("Keep this local project note.", kind="project")
    store.add("Keep this agent note.", kind="agent")

    assert store.search("project") == []
    assert store.clear() == 2
    assert store.stats()["count"] == 0


def test_detect_memory_candidate_direct_save_and_suggestion() -> None:
    direct = detect_memory_candidate("帮我记住，我喜欢中文回答")
    assert direct is not None
    assert direct["action"] == "save"
    assert direct["kind"] == "user_profile"
    assert direct["role"] == ""
    assert direct["content"] == "我喜欢中文回答"

    role_direct = detect_memory_candidate("Hephaestus 写代码时优先保持现有架构")
    assert role_direct is not None
    assert role_direct["action"] == "suggest"
    assert role_direct["kind"] == "agent"
    assert role_direct["role"] == "hephaestus"

    question = detect_memory_candidate("这个项目应该如何设计 memory 模块？")
    assert question is None


def test_memory_suggestion_lifecycle(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")

    suggestion = store.suggest(
        "当前项目叫 Pantheon，是神殿多 agent 协作系统。",
        kind="project",
        role="hermes",
        reason="stable project detail",
    )

    assert suggestion["status"] == "pending"
    assert suggestion["role"] == "hermes"
    assert store.stats()["pending_suggestions"] == 1

    item, saved = store.accept_suggestion(suggestion["id"])
    assert item["source"] == "suggested"
    assert item["role"] == "hermes"
    assert saved["status"] == "saved"
    assert store.suggestions() == []

    second = store.suggest("UI 风格偏简洁高级。", kind="project")
    assert store.ignore_suggestion(second["id"]) is True
    assert store.suggestions() == []


def test_memory_search_uses_global_and_role_scope(tmp_path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite")
    global_item = store.add("所有 agent 都应该优先中文回答。", kind="user_profile")
    hephaestus_item = store.add(
        "Hephaestus 写代码时优先保持现有架构。",
        kind="agent",
        role="hephaestus",
    )
    apollo_item = store.add("Apollo 文案要更有诗意。", kind="agent", role="apollo")

    hephaestus_matches = store.search("代码 agent 中文", role="hephaestus")
    hephaestus_ids = {item["id"] for item in hephaestus_matches}
    assert global_item["id"] in hephaestus_ids
    assert hephaestus_item["id"] in hephaestus_ids
    assert apollo_item["id"] not in hephaestus_ids
