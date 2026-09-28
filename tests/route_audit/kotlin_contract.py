"""Small Gson/Kotlin contract simulator used by route audit tests.

It intentionally models the failure modes that matter to this repository:
missing nullable/non-null keys, absent lists, fractional Int values and
integer overflow. It does not compile Kotlin and it never changes Android code.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ANDROID_SRC = ROOT / "KharazmiAdmin/app/src/main/java"

@dataclass(frozen=True)
class KotlinField:
    name: str
    json_name: str
    type_name: str
    nullable: bool
    line: int

@dataclass
class ContractIssue:
    field: str
    kind: str
    detail: str
    line: int

@dataclass
class ContractResult:
    model: str
    values: dict[str, Any]
    issues: list[ContractIssue]


def _class_block(text: str, start: int) -> str:
    brace = text.find("{", start)
    if brace < 0:
        return ""
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{": depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0: return text[brace + 1:i]
    return text[brace + 1:]


def discover_models(root: Path = ANDROID_SRC) -> dict[str, list[KotlinField]]:
    found: dict[str, list[KotlinField]] = {}
    class_re = re.compile(r"\bdata\s+class\s+(\w+)\s*\(")
    for path in sorted(root.rglob("*.kt")):
        text = path.read_text(encoding="utf-8")
        for match in class_re.finditer(text):
            name = match.group(1)
            block = text[match.end():]
            # Constructor closes at the first balanced ')' (default expressions
            # in this project do not contain Kotlin lambdas).
            depth = 1
            end = 0
            for i, char in enumerate(block):
                if char == "(": depth += 1
                elif char == ")":
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            constructor = block[:end]
            fields: list[KotlinField] = []
            pending_json: str | None = None
            for line_no, line in enumerate(constructor.splitlines(), start=text[:match.end()].count("\n") + 1):
                ann = re.search(r"@SerializedName\(\s*['\"]([^'\"]+)", line)
                if ann: pending_json = ann.group(1)
                # Kotlin data classes in this project commonly keep the whole
                # constructor on one line, so parse every val/var on that line.
                for field in re.finditer(r"\b(?:val|var)\s+(\w+)\s*:\s*([^,)=]+)", line):
                    fname, ftype = field.group(1), field.group(2).strip()
                    nullable = ftype.endswith("?")
                    ftype = ftype.rstrip("?").strip()
                    fields.append(KotlinField(fname, pending_json or fname, ftype, nullable, line_no))
                    pending_json = None
            if fields: found[name] = fields
    return found


def _primitive_default(t: str) -> Any:
    if t in ("Int", "Long", "Short", "Byte", "Float", "Double"): return 0
    if t == "Boolean": return False
    if t == "String": return None
    if t.startswith("List<") or t.startswith("MutableList<"): return []
    return None


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def decode(model: str, payload: dict[str, Any], models: dict[str, list[KotlinField]] | None = None) -> ContractResult:
    models = models or discover_models()
    fields = models.get(model, [])
    values: dict[str, Any] = {}
    issues: list[ContractIssue] = []
    for field in fields:
        present = field.json_name in payload
        value = payload.get(field.json_name)
        if not present or value is None:
            values[field.name] = None if field.nullable else _primitive_default(field.type_name)
            if not present and field.type_name.startswith(("List<", "MutableList<")):
                issues.append(ContractIssue(field.name, "missing-list", "کلید لیست در پاسخ نیست؛ UI آن را خالی می‌بیند", field.line))
            elif not field.nullable and field.type_name in ("String",) or (not field.nullable and field.type_name not in ("Int", "Long", "Short", "Byte", "Float", "Double", "Boolean") and values[field.name] is None):
                issues.append(ContractIssue(field.name, "missing-non-null", "کلید غیرnullable وجود ندارد و استفاده می‌تواند NPE بدهد", field.line))
            continue
        base = field.type_name
        if base == "Int" and _is_number(value) and (isinstance(value, float) and not value.is_integer() or int(value) < -2147483648 or int(value) > 2147483647):
            issues.append(ContractIssue(field.name, "int-parse", f"مقدار {value!r} برای Int قابل parse امن نیست", field.line))
        if base == "Long" and _is_number(value) and (int(value) < -9223372036854775808 or int(value) > 9223372036854775807):
            issues.append(ContractIssue(field.name, "long-overflow", f"مقدار {value!r} از محدوده Long خارج است", field.line))
        values[field.name] = value
    return ContractResult(model, values, issues)


def audit_payload(model: str, payload: dict[str, Any]) -> list[ContractIssue]:
    return decode(model, payload).issues
