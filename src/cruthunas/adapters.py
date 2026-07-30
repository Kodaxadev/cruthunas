from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


TARGETS = (".claude/skills", ".codex/skills")
MANIFEST = ".cruthunas/adapters.json"


def _digest(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _canonical_skills(root: Path) -> list[Path]:
    skills_root = root / "skills"
    if not skills_root.is_dir():
        return []
    return sorted(
        path for path in skills_root.iterdir() if (path / "SKILL.md").is_file()
    )


def sync_adapters(root: Path) -> dict:
    records: dict[str, dict] = {}
    for skill_dir in _canonical_skills(root):
        name = skill_dir.name
        source_hash = _digest(skill_dir / "SKILL.md")
        target_paths: list[str] = []
        for target_root in TARGETS:
            target = root / target_root / name
            if target.exists():
                shutil.rmtree(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(skill_dir, target)
            target_paths.append(str(target.relative_to(root)).replace("\\", "/"))
        records[name] = {
            "source_git_blob_sha": source_hash,
            "targets": target_paths,
        }
    manifest = {"schema_version": 1, "skills": records}
    manifest_path = root / MANIFEST
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def check_adapters(root: Path) -> list[str]:
    manifest_path = root / MANIFEST
    if not manifest_path.is_file():
        return [f"missing {MANIFEST}; run cruthunas adapters sync"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid {MANIFEST}: {exc}"]
    expected = manifest.get("skills", {})
    actual_names = {path.name for path in _canonical_skills(root)}
    errors: list[str] = []
    if actual_names != set(expected):
        errors.append("canonical skill set differs from adapter manifest")
    for name in sorted(actual_names & set(expected)):
        source = root / "skills" / name / "SKILL.md"
        source_hash = _digest(source)
        if expected[name].get("source_git_blob_sha") != source_hash:
            errors.append(f"{name}: manifest source hash is stale")
        for target_text in expected[name].get("targets", []):
            target = root / target_text / "SKILL.md"
            if not target.is_file():
                errors.append(f"{name}: missing adapter {target_text}")
            elif _digest(target) != source_hash:
                errors.append(f"{name}: adapter drift at {target_text}")
    return errors
