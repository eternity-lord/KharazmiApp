"""Execute the all-route smoke, invalid-input and empty-shape sweep.

Usage: python -m tests.route_audit.sweep.run_sweep
The report is intentionally a small JSON artifact in this directory.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from ..seed import seed_database
from .common import inventory, operation, request_parts, role_for, shape

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def run() -> dict:
    with tempfile.TemporaryDirectory(prefix="route-audit-sweep-") as tmp:
        db_path = Path(tmp) / "sweep.db"
        os.environ["JWT_SECRET_KEY"] = "route-audit-sweep-secret-" + "x" * 40
        manifest = seed_database(db_path)
        import sys
        sys.path.insert(0, str(ROOT / "Kharazmi_Server"))
        import main  # type: ignore
        import models  # type: ignore
        from dependencies import create_jwt_token  # type: ignore
        client = TestClient(main.app)
        openapi = client.get("/openapi.json").json()
        # Each route starts from the same post-startup seed snapshot. Without
        # this, DELETE/logout/suspend routes would poison later rows and make
        # the sweep measure ordering rather than route behavior.
        baseline = db_path.read_bytes()
        def reset_db():
            main.models.engine.dispose()
            db_path.write_bytes(baseline)
        rows = inventory()
        report = {"seed": manifest["counts"], "route_count": len(rows), "routes": [], "contract": {}}
        role_users = {"admin": 1, "secretary": 2, "teacher": 3, "student": 4, "parent": 5}
        def fresh_headers(role: str):
            # logout and other stateful auth routes must not poison later rows.
            token = create_jwt_token(role_users[role], role)
            session = models.SessionLocal()
            session.add(models.UserSession(user_id=role_users[role], teacher_id=1 if role == "teacher" else None, sub_role=role, token=token))
            session.commit(); session.close()
            return {"Authorization": f"Bearer {token}"}
        for row in rows:
            reset_db()
            role = role_for(row)
            headers = fresh_headers(role)
            op = operation(openapi, row)
            invalid_target = bool(op.get("requestBody") or op.get("parameters"))
            url, params, _, body = request_parts(openapi, row)
            try:
                response = client.request(row["method"], url, params=params, json=body, headers=headers)
                json_ok, body_shape, value = shape(response)
                error = None
            except Exception as exc:  # keep one broken route from hiding the rest
                response = None; json_ok = False; body_shape = "client-exception"; value = None; error = repr(exc)
            entry = {"method": row["method"], "path": row["path کامل"], "handler": row["handler"], "role": role, "status": response.status_code if response else None, "json": json_ok, "shape": body_shape, "error": error, "invalid_target": invalid_target, "status_500": bool(response and response.status_code == 500)}
            # A second, non-mutating empty read where a query key allows it.
            empty = None
            if row["method"] == "GET" and params:
                empty_params = dict(params)
                for key in empty_params:
                    if key in ("query", "search"): empty_params[key] = "__route_audit_empty__"
                    elif key.endswith("_id") or key in ("id", "student_id"): empty_params[key] = 999999
                try:
                    reset_db()
                    er = client.get(url, params=empty_params, headers=fresh_headers(role))
                    ej, es, ev = shape(er)
                    empty = {"status": er.status_code, "json": ej, "shape": es, "is_null_list": es == "null", "value": ev if isinstance(ev, list) and len(ev) < 3 else None}
                except Exception as exc: empty = {"error": repr(exc)}
            entry["empty"] = empty
            report["routes"].append(entry)

            # Invalid request generated from the OpenAPI operation. Path-type
            # failures use a non-integer path; body/query failures use a wrong
            # primitive. A 500 is always retained for bug classification.
            try:
                reset_db()
                iurl, iparams, _, ibody = request_parts(openapi, row, invalid=True)
                ir = client.request(row["method"], iurl, params=iparams, json=ibody, headers=fresh_headers(role))
                ij, ishape, _ = shape(ir)
                entry["invalid"] = {"status": ir.status_code, "json": ij, "shape": ishape, "status_500": ir.status_code == 500}
            except Exception as exc:
                entry["invalid"] = {"status": None, "error": repr(exc), "status_500": False}
        report["invalid_target_count"] = sum(1 for entry in report["routes"] if entry.get("invalid_target"))
        report["empty_probe_count"] = sum(1 for entry in report["routes"] if entry.get("empty") is not None)
        OUT.joinpath("report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        # CSV is convenient for searching 221 rows in review.
        lines = ["method,path,role,status,json,shape,invalid_status,invalid_json,empty_status,empty_shape"]
        for e in report["routes"]:
            inv = e.get("invalid", {}); emp = e.get("empty") or {}
            vals = [e["method"], e["path"], e["role"], e.get("status"), e.get("json"), e.get("shape"), inv.get("status"), inv.get("json"), emp.get("status"), emp.get("shape")]
            lines.append(",".join('"' + str(v).replace('"', '""') + '"' for v in vals))
        OUT.joinpath("report.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return report


if __name__ == "__main__":
    result = run()
    routes = result["routes"]
    print(json.dumps({"routes": len(routes), "status_500": sum(x["status_500"] for x in routes), "invalid_500": sum(x.get("invalid", {}).get("status_500", False) for x in routes), "non_json": sum(not x["json"] for x in routes)}, ensure_ascii=False))
