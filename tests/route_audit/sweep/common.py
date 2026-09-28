from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SERVER = ROOT / "Kharazmi_Server"


def inventory() -> list[dict[str, str]]:
    with (ROOT / "docs/app-map/server-routes.csv").open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def role_for(row: dict[str, str]) -> str:
    path = row["path کامل"]
    handler = row["handler"]
    # Explicit admin namespace wins over a handler name such as get_student_*.
    if path.startswith("/admin") or path.startswith("/config") or path.startswith("/dashboard"):
        return "admin"
    if "/finance/parent" in path or path.startswith("/parent") or ".parent." in handler:
        return "parent"
    if "/finance/student/" in path or "/reports/student_statement" in path or "/students/my_profile" in path or "/students/{student_id}" in path or "/students/{id}/" in path or "/attendance/student_history" in path or "qr_check-in" in path or "/exams/student" in path or "/exams/attempts" in path or "/homework/student" in path or ".get_student_exams" in handler:
        return "student"
    # Live control is allowed to the class owner; the seed's teacher token is
    # attached to teacher 1. Read-only admin live routes were handled above.
    if "attendance/live/current" in path:
        return "teacher"
    if "start_live" in path or "end_live" in path or "cancel_live" in path or "live_status" in path:
        return "admin"
    if ".teacher" in handler and "/admin" not in path:
        return "teacher"
    if "/auth/" in path and any(x in path for x in ("login", "request_otp", "verify")):
        return "admin"
    return "admin"


def resolve_schema(openapi: dict[str, Any], schema: dict[str, Any] | None) -> dict[str, Any]:
    if not schema:
        return {}
    if "$ref" in schema:
        return openapi["components"]["schemas"].get(schema["$ref"].rsplit("/", 1)[-1], {})
    if "anyOf" in schema:
        choices = [item for item in schema["anyOf"] if item.get("type") != "null"]
        return resolve_schema(openapi, choices[0] if choices else {})
    return schema


def example_value(openapi: dict[str, Any], schema: dict[str, Any], field_name: str = "") -> Any:
    schema = resolve_schema(openapi, schema)
    if "example" in schema: return schema["example"]
    if "default" in schema: return schema["default"]
    if "enum" in schema and schema["enum"]: return schema["enum"][0]
    typ = schema.get("type")
    lname = field_name.lower()
    if typ == "object" or "properties" in schema:
        return {name: example_value(openapi, child, name) for name, child in schema.get("properties", {}).items() if name in schema.get("required", []) or "default" in child}
    if typ == "array": return [example_value(openapi, schema.get("items", {}), field_name)]
    if typ == "integer":
        if "student" in lname: return 1
        if "course" in lname or "class" in lname: return 1
        if "session_code" in lname: return 5001
        return 1
    if typ == "number": return 1.0
    if typ == "boolean": return False
    if typ == "string":
        if "date" in lname: return "1405/06/20"
        if "time" in lname: return "16:00"
        if "status" in lname: return "Present"
        if "mode" in lname: return "metadata_only"
        if "type" in lname: return "deposit"
        if "target_wallet" in lname: return "institute"
        if "payment_method" in lname: return "نقدی"
        if "token" in lname: return "route-audit-token"
        if "mobile" in lname: return "09120000001"
        return "route-audit"
    return None


def path_value(name: str) -> str:
    lname = name.lower()
    if "session_code" in lname: return "5001"
    if "course" in lname or "class" in lname: return "1"
    if "student" in lname: return "1"
    if "transaction" in lname: return "1"
    if "installment" in lname: return "1"
    if "exam" in lname or "attempt" in lname: return "1"
    if "request" in lname: return "1"
    return "1"


def build_url(path: str, *, invalid_path: bool = False) -> str:
    def replace(match: re.Match[str]) -> str:
        return "not-an-integer" if invalid_path else path_value(match.group(1))
    return re.sub(r"\{([^}]+)\}", replace, path)


def operation(openapi: dict[str, Any], row: dict[str, str]) -> dict[str, Any]:
    return openapi["paths"][row["path کامل"]][row["method"].lower()]


def request_parts(openapi: dict[str, Any], row: dict[str, str], *, invalid: bool = False) -> tuple[str, dict[str, Any], dict[str, Any], Any]:
    op = operation(openapi, row)
    url = build_url(row["path کامل"], invalid_path=invalid)
    params: dict[str, Any] = {}
    for param in op.get("parameters", []):
        if param.get("in") == "query" and param.get("required") and not invalid:
            params[param["name"]] = example_value(openapi, param.get("schema", {}), param["name"])
    body = None
    request_body = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema")
    if request_body is not None:
        body = example_value(openapi, request_body)
        if invalid:
            resolved = resolve_schema(openapi, request_body)
            required = resolved.get("required", [])
            if required:
                body = {required[0]: []}
            else:
                body = {}
    if invalid and not request_body:
        required_query = [p for p in op.get("parameters", []) if p.get("in") == "query" and p.get("required")]
        if required_query:
            params[required_query[0]["name"]] = []
    return url, params, {"content-type": "application/json"} if body is not None else {}, body


def shape(response) -> tuple[bool, str, Any]:
    try:
        value = response.json()
    except Exception:
        return False, "non-json", None
    if value is None: return True, "null", value
    if isinstance(value, list): return True, "list", value
    if isinstance(value, dict): return True, "object", value
    return True, "scalar", value
