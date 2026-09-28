"""Run the Kotlin/Gson contract simulator against every unique Retrofit call."""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from ..kotlin_contract import audit_payload, discover_models
from ..seed import seed_database
from .common import inventory, request_parts, role_for

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def norm(path: str) -> str:
    path = path.strip().lstrip("/")
    return re.sub(r"\{[^}]+\}", "{}", path).rstrip("/")


def rows():
    with (ROOT / "docs/app-map/android-api-calls.csv").open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def model_name(response_class: str) -> str | None:
    m = re.search(r"List<([^>]+)>", response_class)
    if m: return m.group(1)
    m = re.search(r"Response<([^>]+)>", response_class)
    if m: return m.group(1)
    if response_class in {"ResponseBody", "BaseActivity()"}: return None
    return response_class


def run():
    with tempfile.TemporaryDirectory(prefix="route-audit-contract-") as tmp:
        os.environ["JWT_SECRET_KEY"] = "route-audit-contract-secret-" + "x" * 40
        db_path = Path(tmp) / "contract.db"
        manifest = seed_database(db_path)
        sys.path.insert(0, str(ROOT / "Kharazmi_Server"))
        import main  # type: ignore
        import models  # type: ignore
        from dependencies import create_jwt_token  # type: ignore
        client = TestClient(main.app)
        openapi = client.get("/openapi.json").json()
        baseline = db_path.read_bytes()
        def reset():
            main.models.engine.dispose(); db_path.write_bytes(baseline)
        user_ids = {"admin": 1, "secretary": 2, "teacher": 3, "student": 4, "parent": 5}
        def headers(role):
            token = create_jwt_token(user_ids[role], role)
            db = models.SessionLocal(); db.add(models.UserSession(user_id=user_ids[role], teacher_id=1 if role == "teacher" else None, sub_role=role, token=token)); db.commit(); db.close()
            return {"Authorization": f"Bearer {token}"}
        server = {(r["method"], norm(r["path کامل"])): r for r in inventory()}
        unique = {}
        for row in rows(): unique.setdefault((row["method"], row["path"]), row)
        models_found = discover_models()
        out = {"declarations": len(rows()), "unique_calls": len(unique), "entries": [], "counts": {"dynamic": 0, "unmatched": 0, "route_non_success": 0, "parse": 0, "npe": 0, "silent_zero": 0, "missing_key": 0}}
        for (method, android_path), android_row in unique.items():
            if android_path.startswith("dynamic "):
                out["counts"]["dynamic"] += 1
                out["entries"].append({"method": method, "path": android_path, "response_class": android_row["response class"], "status": None, "dynamic": True, "issues": []})
                continue
            key = (method, norm(android_path))
            server_row = server.get(key)
            if server_row is None:
                out["counts"]["unmatched"] += 1
                out["entries"].append({"method": method, "path": android_path, "response_class": android_row["response class"], "status": None, "unmatched": True, "issues": []})
                continue
            reset()
            role = role_for(server_row)
            url, params, _, body = request_parts(openapi, server_row)
            try:
                response = client.request(method, url, params=params, json=body, headers=headers(role))
                status = response.status_code
                try: payload = response.json()
                except Exception: payload = None
            except Exception as exc:
                out["entries"].append({"method": method, "path": android_path, "response_class": android_row["response class"], "status": None, "error": repr(exc), "issues": []})
                continue
            entry = {"method": method, "path": android_path, "server_path": server_row["path کامل"], "response_class": android_row["response class"], "role": role, "status": status, "issues": []}
            if status < 200 or status >= 300 or payload is None:
                out["counts"]["route_non_success"] += 1
                entry["route_non_success"] = True
                out["entries"].append(entry); continue
            model = model_name(android_row["response class"])
            entry["model"] = model
            if model is None:
                out["entries"].append(entry); continue
            if model not in models_found:
                entry["issues"] = [{"kind": "model-not-found", "field": "", "detail": f"مدل {model} در source parser پیدا نشد"}]
                out["counts"]["missing_key"] += 1
                out["entries"].append(entry); continue
            payloads = payload if android_row["response class"].startswith("List<") and isinstance(payload, list) else [payload]
            issues = []
            for item in payloads:
                if isinstance(item, dict): issues.extend(audit_payload(model, item))
            entry["issues"] = [issue.__dict__ for issue in issues]
            for issue in issues:
                if issue.kind == "int-parse": out["counts"]["parse"] += 1
                elif issue.kind == "long-overflow": out["counts"]["parse"] += 1
                elif issue.kind == "missing-non-null": out["counts"]["npe"] += 1
                elif issue.kind == "missing-list": out["counts"]["missing_key"] += 1
                elif issue.kind == "silent-zero": out["counts"]["silent_zero"] += 1
            out["entries"].append(entry)
        OUT.joinpath("contract-report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return out


if __name__ == "__main__":
    result = run()
    print(json.dumps(result["counts"] | {"unique_calls": result["unique_calls"], "declarations": result["declarations"]}, ensure_ascii=False))
