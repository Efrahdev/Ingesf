# Ingesf — document ingestion pipeline

Turns **any paper** — PDF (typed or scanned), screenshots and photos, Word, PowerPoint, OpenDocument, HTML — into
a **checked question pack** for the Practice App, with **no AI in the conversion**.

An AI model is used once per layout: it reads a *profiling brief* (made by this program) and writes a *profile*.
After that, deterministic code converts the paper and proves, check by check, that nothing was lost, changed or
invented. A person approves the result against deliberately planted errors before anything is imported.

## Start it in GitHub Codespaces

**Full step-by-step guide: [`docs/CODESPACES_GUIDE.md`](docs/CODESPACES_GUIDE.md).** In short:

1. On GitHub: **Code → Codespaces → Create codespace on main**.
2. Wait for the first setup (about 5–10 minutes the first time: it installs Python and Node packages, Poppler,
   LibreOffice and a headless browser, then runs a quick self-test).
3. The interface opens by itself in a browser tab. If it does not: **Ports** tab → **Ingesf UI (8765)** → open
   in browser. To restart it: `bash .devcontainer/start.sh`.

Your uploads, briefs and runs are kept in `workspace/` inside the codespace (not committed: they hold copies of
your papers). A codespace keeps its files while it exists; download approved packs you want to keep.

## Using the interface

1. **Upload a paper** → **Make the brief**. Download the brief (and, for PDFs, scans and screenshots, the page
   images zip).
2. Give the brief and the images to **any AI model**. Paste its YAML reply in **2 · AI profile** → **Lint** →
   **Try** (side-by-side trial). Repeat until clean. Good profiles can be saved to the library and reused for
   every later paper with the same layout (only a new job is needed).
3. **3 · Run & checks**: the conversion and six gates. A FAIL cannot be waived.
4. **4 · Review & approve**: compare source and result item by item (some items are corrupted on purpose),
   fill in the verdicts, approve, and download `pack.zip` for the Practice App's Import screen.

Everything the interface does is the `ingest/ingest` command underneath, which you can also run in the
codespace terminal — see [`ingest/README.md`](ingest/README.md). The design, the review of the original
specification and what is not built yet are in [`ingest/ARCHITECTURE.md`](ingest/ARCHITECTURE.md).

## Repository

| Path | Contents |
| --- | --- |
| `ui/` | The web interface (Python standard library server + one page). |
| `ingest/` | The pipeline: converter (`engine/`), independent checks (`checker/`), the profiler template (`kit/`), approved profiles and jobs, self-tests. |
| `src/shared/qpack`, `src/client/render.ts`, `docs/` | The Practice App's own pack reader, renderer and schema, copied unchanged: the checks run the app's real code. Keep them in step with the Practice App (see `src/README.md`). |
| `samples/` | Reference papers used by the jobs and tests. |
| `.devcontainer/` | Codespaces setup. |

## Check it

```bash
npm run test:quick     # 36 cases, about 20 seconds
npm test               # 58 cases including the browser checks and approval tampering
npm run papers         # 12 sample papers through the whole corridor
```
