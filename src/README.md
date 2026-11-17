# Practice App code used by the checks

These files are copied **unchanged** from the Practice App repository (`Efrahdev/PracticeApp`, commit `8673324`):

- `shared/qpack/*` — the app's question-pack reader (parse, normalise, compose, fingerprint)
- `client/render.ts` — the app's Markdown + LaTeX renderer
- `../docs/question-pack.schema.json`, `../docs/question-format.md` — the pack format

Gates G2 and G4 call them so that a pack is judged by exactly the code that will read and show it. When the
Practice App changes any of these files, copy the new versions here and run `npm test`.
