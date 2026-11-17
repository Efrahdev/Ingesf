# Ingesf in GitHub Codespaces: the complete guide

Follow the steps in order. Each step says what to do, what you should see, and what to do if you do not see it.
Menu names on github.com can change slightly; the meaning stays the same.

---

## Part A. One-time setup

### A1. Make the repository private
Do this first: the repository contains reference papers, and your uploads can contain papers you do not want public.
1. Open `https://github.com/Efrahdev/Ingesf`.
2. Click **Settings** (top row of tabs).
3. Scroll to the bottom, to **Danger Zone**. Click **Change visibility**, choose **Make private**, and confirm.

### A2. Check your Codespaces allowance
1. Open `https://github.com/settings/billing` and find **Codespaces**.
2. Note the free hours and storage left this month. A 4-core codespace uses 4 core-hours for every hour it runs.
3. Open `https://github.com/settings/codespaces`. Set **Default idle timeout** to the shortest time you are comfortable with (30 minutes is the usual default). A codespace that is idle past this time stops by itself and stops using your hours.

### A3. Create the codespace
1. Open `https://github.com/Efrahdev/Ingesf`.
2. Click the green **Code** button → the **Codespaces** tab → the **...** menu → **New with options...**.
3. Branch: `main`. Machine type: **4-core**. Click **Create codespace**.
   (The setup asks for 4 cores, 8 GB memory and 32 GB storage. If GitHub offers only a 2-core machine, choose it, but the first setup and large PDFs will be slower.)
4. A VS Code window opens in your browser. **Wait.** The first setup takes about 5 to 10 minutes. It installs Python packages, Node packages, Poppler (the independent PDF reader), LibreOffice (for Office files), a headless browser, and then runs a quick self-test.
5. To watch it: press `Ctrl+Shift+P` (Mac: `Cmd+Shift+P`), type `Codespaces: View Creation Log`, press Enter.

**You should see** these final lines in the creation log:
`36 of 36 cases behave as expected` and `Setup finished. The interface starts on port 8765`.

**If setup failed:** press `Ctrl+Shift+P`, type `Codespaces: Rebuild Container`, press Enter. If it fails again, read the last 30 lines of the creation log and send them to me.

### A4. Open the interface
1. A browser tab titled **Ingesf** normally opens by itself.
2. If it does not: click the **Ports** tab (bottom panel of VS Code), find **Ingesf UI (8765)**, and click the globe icon (**Open in Browser**).
3. If **Ports** shows nothing: open the **Terminal** tab and run `bash .devcontainer/start.sh`, then repeat step 2.

**You should see** the page "Turn any paper into a checked question pack".
Leave the port visibility on **Private**. Only you, signed in to GitHub, can open it.

---

## Part B. Convert one paper (do this for every paper)

### B1. Upload the paper
1. Click **Upload a paper** (top right). Choose the file from your computer.
2. Accepted: PDF (typed or scanned), PNG, JPEG, WebP, GIF, BMP, TIFF, a **zip of page images**, Word, PowerPoint, Excel, OpenDocument, RTF, plain text, HTML. Maximum 300 MB.
3. The file appears under **Papers** on the left, with the type the program detected from the file's bytes.

### B2. Make the profiling brief (step "1 · Profiling brief")
1. If the paper is **one paper inside a bigger file** (for example pages 2 to 23 of a 168-page book), type the range in **Pages**, for example `2-23`. Otherwise leave it empty.
2. If the pages have **two columns of text**, set **Columns** to `2`.
3. Click **Make the brief**. Wait until the "working" indicator disappears.
4. Click **Download brief**. If the paper is a PDF, a scan, a screenshot or an Office file, also click **Download page images (zip)** and unzip the zip on your computer.

**You should see** the file size of the brief and thumbnails of the annotated pages. On the images: blue boxes are text lines, orange boxes are figures, green boxes are ink bands (scans), each figure and band has an id such as `p1.u7`, and the red ruler on the left gives the position down the page.

### B3. Get the profile from an AI model
1. Open **any** AI chat (ChatGPT, Claude, Gemini, or another). Start a **new** conversation.
2. **Attach the page images** (every image from the zip) and, if the AI allows it, the original paper.
3. Paste the **entire brief** (open the downloaded file, select all, copy, paste). Do not shorten it.
4. Send. The AI replies with **one YAML code block**, then **Assumptions**, then **Questions for the human**.
5. Answer its questions yourself. Most often: which of your library's difficulty labels each source level maps to. Edit the YAML (job part, `mappings`) to match your answer.
6. Copy **only the contents of the YAML code block** (from the first line to the last, including the line that contains only `---`).

Write down which AI model and conversation made the profile. You need that name at the review step.

### B4. Check the profile (step "2 · AI profile")
1. Click the **2 · AI profile** tab and paste the YAML into the large box.
   (Or pick a ready profile from the dropdown and click **Insert**; then edit its job part: pack id, title, counts, assertions.)
2. Click **Lint**.
   - **"Profile OK"** and a sha256: go on to step 3.
   - **Errors:** each has a line number. Copy the whole message, go back to the **same** AI conversation, and send:
     > Fix the profile. This is the output of the linter. Reply with the full corrected YAML block only.
     Paste the new YAML over the old one and click **Lint** again. Repeat until it says "Profile OK".
3. Click **Try (trial conversion)**. It converts the paper in a scratch area and shows the result. It **cannot** be approved or imported.
   - **"Trial conversion OK"**: look at the side-by-side page below it. Left: the paper. Right: what the app will show. Scroll through at least ten questions, including the first, the last, and any with figures.
   - **"Trial conversion stopped"**: read the message. Send it to the same AI conversation with the same sentence as above. Common messages and what they mean are in Part E.
4. Repeat Lint and Try until the trial is clean and the side-by-side page looks right.

### B5. Record your sign-off of the profile (once the trial is clean)
1. Click **Lint** once more. Copy the long `sha256` value it prints for the profile.
2. In the job part of the YAML (below the line `---`), change the line
   `profile: {id: NAME, version: 1}` to
   `profile: {id: NAME, version: 1, sha256: "PASTE-THE-VALUE-HERE"}`.
3. Click **Lint** again. It must still say "Profile OK".
4. **Do not edit the profile part afterwards.** Any change to the profile changes the sha256 and the run will refuse a mismatch. If you must change it, repeat B4 and B5.

### B6. Save the profile for reuse (optional, recommended)
1. Click **Save to library** and give it a short name, for example `olympiad-pdf-two-column`.
2. The next paper with the same layout: upload it, make no brief, open **2 · AI profile**, choose the saved profile in the dropdown, click **Insert**, and change **only the job part** (file name is irrelevant, change the pack id, title, `expect` counts and `assertions`). The profile part stays as it was and needs no new sign-off.

### B7. Run the pipeline (step "3 · Run & checks")
1. Click the **3 · Run & checks** tab and click **Run the pipeline**. It takes from 10 seconds to a few minutes.
2. Read the result:
   - Each gate (G1 to G6) shows PASS, INFO, WARN or FAIL. Click a gate to see every check.
   - **FAIL** anywhere: you cannot continue. Read the message, fix the profile or job (or the source), and click **Run the pipeline** again.
   - **WARN** is allowed, but you must justify each one at the review step. Expect these four on every run, because they are checks that are not built yet: `G3.formatting`, `G4.layout`, `G6.library_impact` (all "NOT RUN"), and `G1.profile_pin` if you skipped B5.
3. When no gate is FAIL, the page says **Stopped at Gate B. Nothing has been imported.** Go on.

### B8. Review and approve (step "4 · Review & approve")
Do this properly: it is the only protection against a wrong question reaching a learner.
1. Click **What was and was not checked** and read it. It lists exactly what the program verified and what it did not (whether the source's own answers are right is never verified).
2. Click **Decisions made** and read what was ignored, mapped or added.
3. In the review packet (the large panel), go through **every item**. For each item compare the left (source) with the right (what the app will show): every word, number, symbol, figure and answer, attached to the same question.
4. Some items are **corrupted on purpose**. You are not told which. If you find an item that differs from the source, set it to **defect**. If it matches, set it to **ok**. If you cannot tell, set it to **unsure** and look again, because **unsure** blocks approval.
5. Scroll to **Your verdicts**. Set every item.
6. **Reviewer**: type your own name. It must be **different** from the profile author shown next to it. If an AI session does the review, give that session's name (use `review-brief.md`, the **AI reviewer brief** button, as its instructions).
7. **Answers verified**: choose `none` (answers only compared with the source), `sampled` (you independently checked the answers of some items), or `full` (you checked every answer). Be honest: the app uses this to decide how far to trust answer keys.
8. **Numbers checked** appears only for scans and screenshots: choose `full` only after you have checked **every number** against the page picture.
9. **Waivers for warnings**: for each warning listed, type a real reason in one sentence, for example "formatting check not built; bold and italic checked by eye in the packet".
10. Click **Check and approve**.
    - **APPROVED**: the **Download pack.zip** button appears.
    - **REFUSED**: the message names the exact problem. Examples: an item marked `defect` that is a real error (fix the profile or add a correction, then run again); a planted item marked `ok` (the review missed an error: review again, do not just flip the verdict); reviewer equals the author; a warning with no waiver.

### B9. Import into the Practice App
1. Click **Download pack.zip**.
2. In the Practice App, open **Import** and upload `pack.zip`.
3. The Import screen shows a preview before anything is saved: **new**, **changed (new version)**, **already in the library**. Check the counts against what you expect, then save.

Only the pack format is guaranteed: the app's own reader (the same code the Import screen uses) read the pack during gate G2. Automatic checking against your live library (gate G6) is not built, so the preview on the Import screen is your check.

---

## Part C. Keep your work

A codespace keeps its files while it exists, but it is not a backup.

### C1. Keep an approved pack
Open the **Explorer** (left of VS Code), go to `workspace/runs/<run name>/pack/`, right-click `pack.zip` → **Download**. Do the same for `approval.json` if you want the record.

### C2. Keep a profile permanently in the repository
Profiles saved with **Save to library** live only in this codespace (`workspace/library/`). To keep one for good:
1. In the Explorer, open `workspace/library/NAME.yaml`.
2. Copy everything above the line `---` into a new file `ingest/profiles/NAME.yaml`.
3. Copy everything below the line `---` into a new file `ingest/jobs/NAME.yaml`.
4. Open the **Terminal** and run:
   ```
   git add ingest/profiles/NAME.yaml ingest/jobs/NAME.yaml
   git commit -m "Add profile NAME"
   git push
   ```
5. From now on `brief` uses it as a worked example for papers of the same kind, and everyone using the repository gets it.

### C3. Update the pipeline
When I change the repository: in the Terminal run `git pull`, then press `Ctrl+Shift+P` → `Codespaces: Rebuild Container`.

---

## Part D. Daily use, cost and safety

1. **Stop** the codespace when you finish: `https://github.com/codespaces` → the **...** next to it → **Stop codespace**. A stopped codespace uses no core-hours (it still uses storage).
2. **Start** it again from the same page. The interface starts by itself; if it does not, run `bash .devcontainer/start.sh`.
3. **Delete** a codespace you no longer need from the same page. **Download everything you want first** (C1): deletion removes `workspace/`. GitHub also deletes codespaces that stay unused for a long time (see `https://github.com/settings/codespaces` for the retention setting).
4. **Never** change the port visibility to Public, and never share the forwarded link. The interface has no password: GitHub's sign-in is the only protection.
5. The first start of a new codespace repeats the 5 to 10 minute setup. Stopping and starting the **same** codespace does not.

---

## Part E. When something goes wrong

| What you see | What to do |
| --- | --- |
| Interface tab is blank or says it cannot connect | Terminal: `bash .devcontainer/start.sh`, then reload the tab. Log: `workspace/ui.log`. |
| **Ports** tab is empty | Same as above. |
| Upload fails ("file larger than 300 MB") | Split the PDF (use the **Pages** box, or cut the file on your computer). |
| Brief takes very long | A big PDF: type a page range in **Pages** (for example the 20 to 60 pages of one paper). |
| "pdftotext … did not run" or "Poppler" | Terminal: `sudo apt-get install -y poppler-utils`, then run again. |
| "LibreOffice is not installed" or conversion fails | Terminal: `sudo apt-get install -y libreoffice-writer libreoffice-impress libreoffice-calc`. Or save the document as PDF yourself and upload the PDF. |
| Lint: unknown key, regex problem, selector error | Send the message to the AI (B4). The line number points at the exact line. |
| Try or Run: "neither claimed nor ignored", with a list of places | Text exists that no field uses. Send the list to the AI: it must either claim it or add an `ignore` rule with a reason and limits. |
| "ignore rule … swallowed N blocks, over its limit" | The ignore rule is too broad (it may be eating questions). Narrow it. Never just raise the limit without looking at what it matches. |
| "page(s) … have no text layer (scanned)" | That page range is a scan. Use a separate job with the scan route (`kind: scan`, `units@1`) for it. |
| G3 says "the two PDF libraries disagree … `pictures: ["33"]`" | Add the named question to the job: `pictures: ["33"]`. It will then be shown as a picture. Run again. |
| "numerals_checked: full" required | The run has values read off pictures (scan route). Set **Numbers checked** to `full` only after checking every number against the picture. |
| Approval refused | Read the message; each line names the exact fix. Fixing the profile or job means a new **Run** and a new review. |
| Browser tab asks you to sign in again after a long idle | The codespace stopped. Restart it (D2). |

---

## Part F. What is not built yet

- **Live import and library check** (gate G6 and stages S6 to S9): you import by hand through the Practice App's Import screen.
- **Layout check** (line breaks, bold, italic compared with the source) and **formatting count**: shown as warnings "NOT RUN"; check them by eye in the review packet.
- **OCR**: scans become pictures of the page, never text. Answers you or the AI read off a scan are marked **transcribed** and need the full number check.
- The setup in `.devcontainer/` was tested step by step in a normal Linux environment, not inside a real Codespace. If the first creation fails, send the creation log (A3 step 5).
