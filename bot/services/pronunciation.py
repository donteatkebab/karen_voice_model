from __future__ import annotations

import json
import threading
from functools import lru_cache
from pathlib import Path


PRONUNCIATION_PATH = Path(__file__).with_name("pronunciation.json")
PRONUNCIATION_LOCK = threading.RLock()


def _load_raw_rules() -> list[str]:
    if not PRONUNCIATION_PATH.exists():
        return []

    raw = PRONUNCIATION_PATH.read_text(encoding="utf-8").strip()
    if not raw:
        return []

    data = json.loads(raw)
    rules: list[str] = []

    if isinstance(data, list):
        for item in data:
            if isinstance(item, str) and item.strip():
                rules.append(item.strip())
        return rules

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(key, str) and isinstance(value, str):
                key = key.strip()
                value = value.strip()
                if key and value:
                    rules.append(f"{key} -> {value}")
        return rules

    raise ValueError("pronunciation.json must contain a JSON list or object")


@lru_cache(maxsize=1)
def load_pronunciation_rules() -> list[str]:
    with PRONUNCIATION_LOCK:
        return _load_raw_rules()


def _write_pronunciation_rules(rules: list[str]) -> None:
    with PRONUNCIATION_LOCK:
        PRONUNCIATION_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = PRONUNCIATION_PATH.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(rules, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(PRONUNCIATION_PATH)
        load_pronunciation_rules.cache_clear()


def add_pronunciation_rule(rule: str) -> list[str]:
    rule = rule.strip()
    if not rule:
        raise ValueError("Rule cannot be empty")

    rules = load_pronunciation_rules()
    if rule not in rules:
        rules.append(rule)
        _write_pronunciation_rules(rules)
    return rules


def remove_pronunciation_rule(rule: str) -> list[str]:
    rule = rule.strip()
    if not rule:
        raise ValueError("Rule cannot be empty")

    rules = load_pronunciation_rules()
    rules = [item for item in rules if item != rule]
    _write_pronunciation_rules(rules)
    return rules


def format_pronunciation_rules(limit: int | None = None) -> str:
    rules = load_pronunciation_rules()
    if not rules:
        return "دیکشنری/قواعد تلفظ خالی است."
    if limit is not None:
        rules = rules[:limit]
    return "\n".join(f"- {rule}" for rule in rules)

