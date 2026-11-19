# CLAUDE.md — Ingesf

A document ingestion pipeline that turns **any question paper** (PDF, scan, screenshot, Word/PowerPoint/
OpenDocument, HTML) into a **checked question pack** for the Practice App (`Efrahdev/PracticeApp`), with **no AI
in the conversion**. An AI writes a *profile* (layout description) once per layout from a machine-made brief;
deterministic code then converts, and independent gates prove nothing was lost, changed or invented. A person
approves the result (Gate B) before it is imported into the app by hand.

Docs to read before non-trivial changes: `README.md` (overview), `ingest/README.md` (the CLI loop, commands,
exit codes), `ingest/ARCHITECTURE.md` (design, rules R1–R20, what isn't built yet).

## Commands

Run from the repo root. Needs Python 3.11+ (`pip install -r requirements.txt`, pinned lock in
`ingest/requirements.lock`), Node 20+ (`npm ci`), Playwright Chromium, Poppler (`pdftotext`, `pdftoppm`), and
LibreOffice for Office files. `.devcontainer/setup.sh` installs all of it (Codespaces).

```bash
npm run test:quick   # 36 cases, ~20 s, skips browser gates and Gate B cases
npm test             # 58 cases incl. browser checks and approval tampering
npm run papers       # 12 sample papers through the whole corridor + golden oracle
npm run ui           # web UI on :8765 (thin wrapper over the CLI; workspace/ holds uploads and runs)
ingest/ingest <probe|brief|lint|try|run|status|approve-check|oracle> ...   # the CLI; every command takes --json
```

Note: the docs mention `npm run ingest:test`; that script doesn't exist — it is `npm test`.

## Layout

| Path | What |
| --- | --- |
| `ingest/ingest` | Launcher: `python3 -I ingest/engine/cli.py` |
| `ingest/engine/` | Python converter: stages S0–S5 (`stages.py`, `runner.py`), gates G1/G5/G6 (`gates.py`), routes per kind (`html_adapter.py`, `docx_kind.py`, `json_kind.py`, `pages.py`/`probe_pages.py`/`interp_pages.py` for PDF/scan/office), approval (`approve.py`), strict YAML (`yamlstrict.py`) |
| `ingest/checker/` | Node gates G2/G3/G4, picture checks, side-by-side page. **Deliberately shares no code or parser with `engine/`** |
| `ingest/kit/` | Profiler prompt, profile-language reference, profile/job JSON Schemas (fed into every brief) |
| `ingest/profiles/`, `ingest/jobs/` | Approved layouts and per-paper jobs (also worked examples in briefs) |
| `ingest/packs/` | Golden oracle packs from the earlier hand-written converters; differences explained in `ingest/oracle-diffs.yaml` |
| `ingest/tests/` | `run_tests.py` (unit + fault injection + tamper cases), `run_all_papers.sh`, scan/screenshot samples |
| `ui/` | Stdlib-only Python server + one static page |
| `src/shared/qpack/`, `src/client/render.ts`, `docs/` | **Copied unchanged from PracticeApp** so gates judge packs with the app's real code |
| `samples/` | Reference source papers used by jobs and tests |

Git-ignored (hold copies of the user's papers): `ingest/runs/`, `ingest/scratch/`, `workspace/`.

## Rules that must not be broken

- **No AI, no network, no OCR in the corridor (S0–S5).** Conversion is deterministic code only. Scans become
  exact pictures of page regions, never guessed text.
- **Never invent** (R3): absent answers stay absent; every learner-visible field must trace back to claimed
  source blocks (G3.invented).
- **Fail loud** (R2): raise `StageFail` with check id, locator and next action. Exit codes: 0 pass, 10 warnings,
  20 fail, 30 usage, 40 internal bug. A gate FAIL can never be waived.
- **Determinism** (R1): canonical JSON (sorted keys, NFC, LF), fixed-time stored zip. Same inputs → same pack hash.
- **Checker independence**: don't import engine code into `checker/` or vice versa.
- **Every check must be proven able to fail**: when adding a gate or check, add a fault-injection case to
  `ingest/tests/run_tests.py` that it catches.
- Profiles are declarative; `hooks` must stay empty (no AI-written code).
- Human fixes go in a `--corrections` file, never hand-edited into a pack.
- Always run Python with `-I` (isolated) as the launcher and scripts do.

## Keeping in step with PracticeApp

`src/shared/qpack/*`, `src/client/render.ts`, `docs/question-format.md`, `docs/question-pack.schema.json` must
match `Efrahdev/PracticeApp` exactly (currently from commit `8673324`, recorded in `src/README.md`). Never edit
them here; copy new versions over from the app, update the commit in `src/README.md`, and run `npm test`.

## Style

Docs and UI copy use plain British English. Commit messages are a plain sentence describing the change.
