from __future__ import annotations

from pathlib import Path

from cruthunas.adapters import check_adapters, sync_adapters


def test_adapter_hash_is_stable_across_checkout_line_endings(tmp_path: Path) -> None:
    source = tmp_path / "skills/example/SKILL.md"
    source.parent.mkdir(parents=True)
    crlf_content = b"---\r\nname: example\r\n---\r\n# Example\r\n"
    lf_content = crlf_content.replace(b"\r\n", b"\n")
    source.write_bytes(crlf_content)

    sync_adapters(tmp_path)
    assert check_adapters(tmp_path) == []

    # Simulate Git checking out the canonical source and generated copies with
    # different platform line endings while preserving identical text.
    source.write_bytes(lf_content)
    (tmp_path / ".claude/skills/example/SKILL.md").write_bytes(crlf_content)
    (tmp_path / ".codex/skills/example/SKILL.md").write_bytes(lf_content)

    assert check_adapters(tmp_path) == []


def test_adapter_hash_still_detects_content_drift(tmp_path: Path) -> None:
    source = tmp_path / "skills/example/SKILL.md"
    source.parent.mkdir(parents=True)
    source.write_text("---\nname: example\n---\n# Example\n", encoding="utf-8")

    sync_adapters(tmp_path)
    (tmp_path / ".claude/skills/example/SKILL.md").write_text(
        "---\nname: example\n---\n# Changed\n",
        encoding="utf-8",
    )

    assert any("adapter drift" in item for item in check_adapters(tmp_path))
