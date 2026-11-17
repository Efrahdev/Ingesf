#!/usr/bin/env python3 -I
"""Web interface for the ingestion pipeline. Standard library only.

It is a thin layer over the `ingest/ingest` command: every button runs the same command you could type, and
shows its output. Nothing here converts or checks anything itself.

    python3 -I ui/server.py [--port 8765] [--host 0.0.0.0]

Workspace (uploads, briefs, trials, runs): ./workspace (not committed: it holds copies of your papers).
"""
from __future__ import annotations

import argparse
import datetime
import email.parser
import email.policy
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import traceback
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / "ingest" / "ingest"
STATIC = Path(__file__).resolve().parent / "static"
WORK = ROOT / "workspace"
UPLOADS = WORK / "uploads"
RUNS = WORK / "runs"
MAX_UPLOAD = 300 * 1024 * 1024

sys.path.insert(0, str(ROOT / "ingest" / "engine"))
import stages  # noqa: E402  (format detection only)

JOBS: dict[str, dict] = {}
LOCK = threading.Lock()


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_name(name: str) -> str:
    base = Path(name).name.strip() or "upload"
    return re.sub(r"[^\w .()\-]+", "_", base)[:150]


def upload_dir(uid: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{12}", uid or ""):
        raise ValueError("bad upload id")
    d = UPLOADS / uid
    if not d.is_dir():
        raise FileNotFoundError(f"no upload {uid}")
    return d


def meta(uid: str) -> dict:
    return json.loads((upload_dir(uid) / "meta.json").read_text(encoding="utf-8"))


def save_meta(uid: str, m: dict) -> None:
    (UPLOADS / uid / "meta.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")


def run_cli(args: list[str], timeout: int = 1800) -> dict:
    p = subprocess.run([str(INGEST), *args], capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
    log = [ln for ln in p.stderr.splitlines() if not ln.startswith("{")]
    return {"code": p.returncode, "out": p.stdout, "err": "\n".join(log[-60:]), "cmd": "ingest/ingest " + " ".join(a if " " not in a else f'"{a}"' for a in args)}


def start_job(kind: str, fn) -> str:
    jid = uuid.uuid4().hex[:12]
    with LOCK:
        JOBS[jid] = {"id": jid, "kind": kind, "status": "running", "started": now(), "result": None}

    def work():
        try:
            res = fn()
            status = "done"
        except Exception as e:  # noqa: BLE001
            res, status = {"code": 40, "out": "", "err": "".join(traceback.format_exception(e))[-3000:]}, "error"
        with LOCK:
            JOBS[jid].update(status=status, result=res, ended=now())
    threading.Thread(target=work, daemon=True).start()
    return jid


# ------------------------------------------------------------------ actions
def act_brief(body: dict) -> dict:
    uid = body["upload"]
    d, m = upload_dir(uid), meta(uid)
    out = d / "brief.md"
    args = ["brief", str(d / m["file"]), "--out", str(out)]
    if body.get("pages"):
        args += ["--pages", str(body["pages"])]
    if str(body.get("columns", "1")) == "2":
        args += ["--columns", "2"]
    res = run_cli(args, timeout=900)
    imgs_dir = d / "brief-pages"
    images = sorted(str(p.relative_to(WORK)) for p in imgs_dir.rglob("*.png")) if imgs_dir.exists() else []
    if images:   # a zip of the page images, for attaching to the AI in one go
        shutil.make_archive(str(d / "page-images"), "zip", imgs_dir)
    res.update(brief=str(out.relative_to(WORK)) if out.exists() else None, images=images,
               images_zip=str((d / "page-images.zip").relative_to(WORK)) if images else None,
               brief_chars=out.stat().st_size if out.exists() else 0)
    m["brief"] = res["brief"]
    save_meta(uid, m)
    return res


def act_lint(body: dict) -> dict:
    uid = body["upload"]
    d = upload_dir(uid)
    (d / "profile.yaml").write_text(body["yaml"], encoding="utf-8")
    res = run_cli(["lint", str(d / "profile.yaml"), "--json"], timeout=120)
    try:
        res["lint"] = json.loads(res["out"])
    except ValueError:
        res["lint"] = None
    m = meta(uid)
    m["profile_saved"] = now()
    save_meta(uid, m)
    return res


def act_try(body: dict) -> dict:
    uid = body["upload"]
    d, m = upload_dir(uid), meta(uid)
    if body.get("yaml"):
        (d / "profile.yaml").write_text(body["yaml"], encoding="utf-8")
    out = d / "try"
    res = run_cli(["try", str(d / "profile.yaml"), "--source", str(d / m["file"]), "--out", str(out)], timeout=1800)
    res["page"] = str((out / "try.html").relative_to(WORK)) if (out / "try.html").exists() else None
    res["pack"] = str((out / "pack" / "pack.json").relative_to(WORK)) if (out / "pack" / "pack.json").exists() else None
    return res


def act_run(body: dict) -> dict:
    uid = body["upload"]
    d, m = upload_dir(uid), meta(uid)
    if body.get("yaml"):
        (d / "profile.yaml").write_text(body["yaml"], encoding="utf-8")
    args = ["run", str(d / "profile.yaml"), "--source", str(d / m["file"]), "--runs-dir", str(RUNS), "--json"]
    corr = d / "corrections.yaml"
    if corr.exists() and corr.read_text(encoding="utf-8").strip():
        args += ["--corrections", str(corr)]
    res = run_cli(args, timeout=3600)
    try:
        res["run"] = json.loads(res["out"])
        m.setdefault("runs", []).append(Path(res["run"]["run_dir"]).name)
        save_meta(uid, m)
    except (ValueError, KeyError):
        res["run"] = None
    return res


def run_dir(name: str) -> Path:
    if not re.fullmatch(r"[\w.\-]+", name or ""):
        raise ValueError("bad run name")
    d = RUNS / name
    if not (d / "manifest.json").exists():
        raise FileNotFoundError(f"no run {name}")
    return d


def run_summary(name: str) -> dict:
    d = run_dir(name)
    m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    gates = {}
    for g in sorted((d / "gates").glob("g?.json")):
        v = json.loads(g.read_text(encoding="utf-8"))
        gates[v["gate"]] = {"status": v["status"], "selftest": (v.get("selftest") or {}).get("status"),
                            "checks": [{"id": c["id"], "status": c["status"], "message": c["message"], "examined": c.get("examined")} for c in v["checks"]]}
    rel = lambda p: str(p.relative_to(WORK)) if p.exists() else None   # noqa: E731
    out = {"name": name, "manifest": m, "gates": gates, "approved": (d / "approval.receipt.json").exists(),
           "review": rel(d / "review" / "index.html"), "assurance": rel(d / "review" / "assurance.md"), "decisions": rel(d / "review" / "decisions-made.md"),
           "summary": rel(d / "review" / "summary.md"), "brief": rel(d / "review" / "review-brief.md"),
           "pack_zip": rel(d / "pack" / "pack.zip"), "pack_json": rel(d / "pack" / "pack.json")}
    tpl = d / "review" / "approval.template.json"
    if tpl.exists():
        out["template"] = json.loads(tpl.read_text(encoding="utf-8"))
    if (d / "approval.json").exists():
        out["approval"] = json.loads((d / "approval.json").read_text(encoding="utf-8"))
    return out


def list_runs() -> list[dict]:
    rows = []
    for d in sorted(RUNS.glob("*/manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            m = json.loads(d.read_text(encoding="utf-8"))
        except ValueError:
            continue
        s4 = m.get("stages", {}).get("S4", {})
        failed = [k for k, v in m.get("stages", {}).items() if v.get("status") == "FAIL"]
        rows.append({"name": d.parent.name, "source": (m.get("sources") or [{}])[0].get("name"), "profile": m.get("profile", {}).get("id"),
                     "questions": m.get("pack", {}).get("question_count"), "pictures": m.get("pack", {}).get("asset_count"),
                     "status": "FAIL" if failed else s4.get("status", "?"), "approved": (d.parent / "approval.receipt.json").exists(),
                     "started": m.get("started")})
    return rows


def act_approve(body: dict) -> dict:
    d = run_dir(body["run"])
    approval = body["approval"]
    approval.setdefault("approved_at", now())
    (d / "approval.json").write_text(json.dumps(approval, indent=2, ensure_ascii=False), encoding="utf-8")
    return run_cli(["approve-check", str(d)], timeout=300)


def list_uploads() -> list[dict]:
    rows = []
    for mf in sorted(UPLOADS.glob("*/meta.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            m = json.loads(mf.read_text(encoding="utf-8"))
        except ValueError:
            continue
        d = mf.parent
        m["has_profile"] = (d / "profile.yaml").exists()
        rows.append(m)
    return rows


def library() -> list[dict]:
    """Approved profiles that ship with the pipeline (worked examples) and ones saved from this interface."""
    out = []
    for folder, origin in ((ROOT / "ingest" / "profiles", "built-in"), (WORK / "library", "saved")):
        for p in sorted(folder.glob("*.yaml")) if folder.exists() else []:
            out.append({"name": p.stem, "origin": origin, "path": str(p.relative_to(ROOT))})
    return out


# ------------------------------------------------------------------ HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "IngestUI/1.0"

    def log_message(self, fmt, *args):   # quieter log
        sys.stderr.write("%s %s\n" % (now(), fmt % args))

    def send_json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path: Path, download: bool = False):
        if not path.is_file():
            return self.send_json({"error": "not found"}, 404)
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix in (".md", ".yaml", ".yml"):
            ctype = "text/plain; charset=utf-8"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        self.wfile.write(data)

    def body_json(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        try:
            url = urlparse(self.path)
            path = unquote(url.path)
            if path in ("/", "/index.html"):
                return self.send_file(STATIC / "index.html")
            if path.startswith("/static/"):
                f = (STATIC / path[len("/static/"):]).resolve()
                if STATIC.resolve() in f.parents:
                    return self.send_file(f)
                return self.send_json({"error": "forbidden"}, 403)
            if path.startswith("/files/"):
                f = (WORK / path[len("/files/"):]).resolve()
                if WORK.resolve() not in f.parents:
                    return self.send_json({"error": "forbidden"}, 403)
                return self.send_file(f, download="download=1" in (url.query or ""))
            if path == "/api/uploads":
                return self.send_json(list_uploads())
            if path.startswith("/api/upload/"):
                uid = path.rsplit("/", 1)[-1]
                m = meta(uid)
                d = upload_dir(uid)
                m["profile_yaml"] = (d / "profile.yaml").read_text(encoding="utf-8") if (d / "profile.yaml").exists() else ""
                m["corrections_yaml"] = (d / "corrections.yaml").read_text(encoding="utf-8") if (d / "corrections.yaml").exists() else ""
                return self.send_json(m)
            if path == "/api/runs":
                return self.send_json(list_runs())
            if path.startswith("/api/run/"):
                return self.send_json(run_summary(path.rsplit("/", 1)[-1]))
            if path.startswith("/api/jobs/"):
                jid = path.rsplit("/", 1)[-1]
                with LOCK:
                    j = JOBS.get(jid)
                return self.send_json(j or {"error": "no such job"}, 200 if j else 404)
            if path == "/api/library":
                return self.send_json(library())
            if path.startswith("/api/profile-text/"):
                rel = path[len("/api/profile-text/"):]
                f = (ROOT / rel).resolve()
                if f.suffix == ".yaml" and ((ROOT / "ingest" / "profiles").resolve() in f.parents or (WORK / "library").resolve() in f.parents):
                    text = f.read_text(encoding="utf-8")
                    jobs = sorted((ROOT / "ingest" / "jobs").glob("*.yaml"))
                    pid = re.search(r"id:\s*([\w-]+)", text)
                    job = next((j.read_text(encoding="utf-8") for j in jobs if pid and re.search(rf"profile:\s*{{id:\s*{re.escape(pid.group(1))}\b", j.read_text(encoding="utf-8"))), "")
                    return self.send_json({"profile": text, "example_job": job})
                return self.send_json({"error": "forbidden"}, 403)
            return self.send_json({"error": "not found"}, 404)
        except (FileNotFoundError, ValueError) as e:
            return self.send_json({"error": str(e)}, 404)
        except Exception as e:  # noqa: BLE001
            return self.send_json({"error": f"{type(e).__name__}: {e}"}, 500)

    def do_POST(self):
        try:
            path = urlparse(self.path).path
            if path == "/api/upload":
                return self.upload()
            body = self.body_json()
            if path == "/api/brief":
                return self.send_json({"job": start_job("brief", lambda: act_brief(body))})
            if path == "/api/lint":
                return self.send_json(act_lint(body))
            if path == "/api/try":
                return self.send_json({"job": start_job("try", lambda: act_try(body))})
            if path == "/api/run":
                return self.send_json({"job": start_job("run", lambda: act_run(body))})
            if path == "/api/approve":
                return self.send_json(act_approve(body))
            if path == "/api/corrections":
                d = upload_dir(body["upload"])
                (d / "corrections.yaml").write_text(body.get("yaml", ""), encoding="utf-8")
                return self.send_json({"saved": True})
            if path == "/api/library/save":
                d = upload_dir(body["upload"])
                name = re.sub(r"[^\w-]+", "-", body.get("name") or "profile").strip("-")[:60] or "profile"
                (WORK / "library").mkdir(parents=True, exist_ok=True)
                shutil.copyfile(d / "profile.yaml", WORK / "library" / f"{name}.yaml")
                return self.send_json({"saved": f"workspace/library/{name}.yaml"})
            return self.send_json({"error": "not found"}, 404)
        except (FileNotFoundError, ValueError, KeyError) as e:
            return self.send_json({"error": str(e)}, 400)
        except Exception as e:  # noqa: BLE001
            return self.send_json({"error": f"{type(e).__name__}: {e}"}, 500)

    def upload(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAX_UPLOAD:
            return self.send_json({"error": f"file larger than {MAX_UPLOAD // 1024 // 1024} MB"}, 413)
        raw = self.rfile.read(n)
        msg = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
            b"Content-Type: " + self.headers["Content-Type"].encode() + b"\r\n\r\n" + raw)
        part = next((p for p in msg.iter_parts() if p.get_param("name", header="content-disposition") == "file"), None)
        if part is None:
            return self.send_json({"error": "no file in the upload"}, 400)
        name = safe_name(part.get_filename() or "upload")
        data = part.get_payload(decode=True) or b""
        uid = uuid.uuid4().hex[:12]
        d = UPLOADS / uid
        d.mkdir(parents=True)
        (d / name).write_bytes(data)
        kind = stages.detect_kind(data, name)
        m = {"id": uid, "file": name, "bytes": len(data), "detected": kind, "uploaded": now()}
        save_meta(uid, m)
        return self.send_json(m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("INGEST_UI_PORT", 8765)))
    ap.add_argument("--host", default="0.0.0.0")
    a = ap.parse_args()
    for p in (UPLOADS, RUNS):
        p.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"Ingest UI on http://localhost:{a.port}  (workspace: {WORK})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
