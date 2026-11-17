// Ingesf web interface. Every button calls the same `ingest/ingest` command you could type; output is shown as is.
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const file = (rel) => "/files/" + rel.split("/").map(encodeURIComponent).join("/");
let current = null; // upload id
let lastRun = null; // run name

async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({ error: `HTTP ${r.status}` }));
  if (!r.ok || j.error) throw new Error(j.error || `HTTP ${r.status}`);
  return j;
}
async function job(path, body, spin) {
  spin.hidden = false;
  try {
    const { job } = await api(path, body);
    for (;;) {
      await new Promise((r) => setTimeout(r, 1200));
      const j = await api("/api/jobs/" + job);
      if (j.status !== "running") return j.result;
    }
  } finally { spin.hidden = true; }
}
const cmdBlock = (res) => `<details><summary class="muted">command and output (exit ${res.code})</summary><pre>$ ${esc(res.cmd || "")}\n${esc(res.out)}${res.err ? "\n" + esc(res.err) : ""}</pre></details>`;

// ------------------------------------------------------------ lists
async function refresh() {
  const [ups, runs] = await Promise.all([api("/api/uploads"), api("/api/runs")]);
  $("#uploads").innerHTML = ups.map((u) => `<li data-id="${u.id}" class="${u.id === current ? "on" : ""}">${esc(u.file)}<small>${esc(u.detected)} · ${Math.round(u.bytes / 1024)} KB${u.has_profile ? " · profile" : ""}</small></li>`).join("") || `<li class="muted">none yet</li>`;
  $("#runs").innerHTML = runs.map((r) => `<li data-run="${esc(r.name)}" class="${r.name === lastRun && !current ? "on" : ""}"><span class="badge ${r.approved ? "PASS" : r.status}">${r.approved ? "APPROVED" : r.status}</span> ${esc(r.source || r.name)}<small>${r.questions ?? "?"} questions · ${esc(r.profile || "")}</small></li>`).join("") || `<li class="muted">none yet</li>`;
}
$("#uploads").addEventListener("click", (e) => { const li = e.target.closest("li[data-id]"); if (li) openUpload(li.dataset.id); });
$("#runs").addEventListener("click", (e) => { const li = e.target.closest("li[data-run]"); if (li) openRun(li.dataset.run); });

// ------------------------------------------------------------ upload
$("#file").addEventListener("change", async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  const fd = new FormData();
  fd.append("file", f);
  const r = await fetch("/api/upload", { method: "POST", body: fd });
  const m = await r.json();
  e.target.value = "";
  if (m.error) return alert(m.error);
  await refresh();
  openUpload(m.id);
});

function showStep(n) {
  document.querySelectorAll("#steps button").forEach((b) => b.classList.toggle("on", b.dataset.step === String(n)));
  document.querySelectorAll(".step").forEach((s) => (s.hidden = s.dataset.step !== String(n)));
}
$("#steps").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { showStep(b.dataset.step); if (b.dataset.step === "4") showReview(); } });

async function openUpload(id) {
  current = id;
  const m = await api("/api/upload/" + id);
  $("#welcome").hidden = true; $("#runview").hidden = true; $("#paper").hidden = false;
  $("#p-name").textContent = m.file;
  const route = { pdf: "PDF", image: "image / screenshot", office: "office document (printed to pages by LibreOffice)", docx: "Word", html: "HTML", unknown: "unknown format" }[m.detected] || m.detected;
  $("#p-meta").textContent = `${route} · ${Math.round(m.bytes / 1024)} KB · uploaded ${m.uploaded}`;
  $("#yaml").value = m.profile_yaml || "";
  $("#corr").value = m.corrections_yaml || "";
  $("#b-out").innerHTML = m.brief ? `<p><a class="btn" href="${file(m.brief)}" target="_blank">Open the existing brief</a></p>` : "";
  $("#y-out").innerHTML = ""; $("#r-out").innerHTML = "";
  lastRun = (m.runs || []).slice(-1)[0] || null;
  if (lastRun) showRunInto($("#r-out"), lastRun);
  showStep(m.profile_yaml ? 2 : 1);
  refresh();
}

// ------------------------------------------------------------ step 1: brief
$("#b-go").addEventListener("click", async () => {
  const res = await job("/api/brief", { upload: current, pages: $("#b-pages").value.trim(), columns: $("#b-columns").value }, $("#b-spin"));
  let h = "";
  if (res.brief) {
    h += `<div class="note"><b>Next:</b> give the brief${res.images.length ? " <b>and the page images</b>" : ""} to any AI model (ChatGPT, Claude, Gemini…). Save its YAML reply and paste it in step 2.</div>
      <div class="row"><a class="btn primary" href="${file(res.brief)}?download=1">Download brief (${Math.round(res.brief_chars / 1024)} KB)</a>
      <button class="btn" id="copy-brief">Copy brief to clipboard</button>
      <a class="btn" href="${file(res.brief)}" target="_blank">Open</a>
      ${res.images_zip ? `<a class="btn" href="${file(res.images_zip)}?download=1">Download ${res.images.length} page images (zip)</a>` : ""}</div>`;
    if (res.images.length) h += `<div class="thumbs">${res.images.slice(0, 24).map((i) => `<a href="${file(i)}" target="_blank"><img src="${file(i)}" loading="lazy" alt=""><span>${esc(i.split("/").pop())}</span></a>`).join("")}</div>`;
  } else h += `<p class="bad">The brief could not be made.</p>`;
  $("#b-out").innerHTML = h + cmdBlock(res);
  const cb = $("#copy-brief");
  if (cb) cb.onclick = async () => { const t = await (await fetch(file(res.brief))).text(); await navigator.clipboard.writeText(t); cb.textContent = "Copied"; };
});

// ------------------------------------------------------------ step 2: profile
async function loadLibrary() {
  const lib = await api("/api/library");
  $("#lib").innerHTML = `<option value="">Start from a library profile…</option>` + lib.map((p) => `<option value="${esc(p.path)}">${esc(p.name)} (${p.origin})</option>`).join("");
}
$("#lib-load").addEventListener("click", async () => {
  const p = $("#lib").value;
  if (!p) return;
  const t = await api("/api/profile-text/" + p);
  $("#yaml").value = t.profile.trim() + "\n---\n" + (t.example_job ? t.example_job.replace(/^\s*-\s*\{file:[^\n]*$/m, "  - {file: \"(replaced by the uploaded file)\", role: paper}").trim() : "job:\n  id: my-paper\n") + "\n";
});
function lintHtml(res) {
  const l = res.lint;
  if (!l) return `<p class="bad">Lint could not read the file.</p>`;
  const msgs = (l.messages || []).map((m) => `<li class="${m.startsWith("ERROR") ? "bad" : "muted"}">${esc(m)}</li>`).join("");
  return (l.errors ? `<p class="bad"><b>${l.errors} error(s).</b> Fix every one (or paste them back to the AI) and lint again.</p>` : `<p class="ok"><b>Profile OK.</b> sha256 <code>${esc(l.profile_sha256 || "")}</code>${l.job_sha256 ? "" : " — no job yet"}</p>`) + (msgs ? `<ul>${msgs}</ul>` : "");
}
$("#y-lint").addEventListener("click", async () => {
  $("#y-spin").hidden = false;
  try { const res = await api("/api/lint", { upload: current, yaml: $("#yaml").value }); $("#y-out").innerHTML = lintHtml(res) + cmdBlock(res); }
  catch (e) { $("#y-out").innerHTML = `<p class="bad">${esc(e.message)}</p>`; }
  finally { $("#y-spin").hidden = true; refresh(); }
});
$("#y-try").addEventListener("click", async () => {
  await api("/api/lint", { upload: current, yaml: $("#yaml").value });
  const res = await job("/api/try", { upload: current, yaml: $("#yaml").value }, $("#y-spin"));
  const ok = res.code === 0;
  $("#y-out").innerHTML = `<p class="${ok ? "ok" : "bad"}"><b>${ok ? "Trial conversion OK." : "Trial conversion stopped."}</b> ${ok ? "Check the side-by-side page, then go to step 3." : "Read the message below; paste it back to the AI or fix the YAML."}</p>
    <pre>${esc(res.out)}</pre>${res.page ? `<iframe class="view" src="${file(res.page)}"></iframe>` : ""}${cmdBlock(res)}`;
});
$("#y-save-lib").addEventListener("click", async () => {
  const name = prompt("Name for this profile in the library:", ($("#yaml").value.match(/id:\s*([\w-]+)/) || [])[1] || "profile");
  if (!name) return;
  await api("/api/lint", { upload: current, yaml: $("#yaml").value });
  const r = await api("/api/library/save", { upload: current, name });
  alert("Saved to " + r.saved); loadLibrary();
});
$("#corr-save").addEventListener("click", async () => { await api("/api/corrections", { upload: current, yaml: $("#corr").value }); alert("Corrections saved. They apply on the next run."); });

// ------------------------------------------------------------ step 3: run
$("#r-go").addEventListener("click", async () => {
  await api("/api/lint", { upload: current, yaml: $("#yaml").value });
  const res = await job("/api/run", { upload: current, yaml: $("#yaml").value }, $("#r-spin"));
  if (res.run) { lastRun = res.run.run_id; await showRunInto($("#r-out"), lastRun); }
  else $("#r-out").innerHTML = `<p class="bad"><b>The run stopped before the checks.</b></p><pre>${esc(res.out)}\n${esc(res.err)}</pre>`;
  refresh();
});

function gatesHtml(s) {
  const m = s.manifest;
  const stopped = Object.entries(m.stages || {}).filter(([, v]) => v.status === "FAIL" && v.message);
  let h = `<p><b>${m.pack ? `${m.pack.question_count} questions, ${m.pack.asset_count} pictures` : "no pack"}</b> · run <code>${esc(s.name)}</code>${s.approved ? ` · <span class="badge PASS">APPROVED</span>` : ""}</p>`;
  for (const [st, v] of stopped) h += `<p class="bad"><b>${st} stopped:</b> ${esc(v.message)}${v.next ? `<br><span class="muted">next: ${esc(v.next)}</span>` : ""}</p>`;
  h += Object.entries(s.gates).map(([g, v]) => `<details class="gate" ${v.status === "FAIL" ? "open" : ""}><summary><span class="badge ${v.status}">${v.status}</span> <b>${g}</b> <span class="muted">${v.checks.length} checks · self-test ${v.selftest || "–"}</span></summary>
    <table>${v.checks.map((c) => `<tr><td><span class="badge ${c.status}">${c.status}</span></td><td><code>${esc(c.id)}</code></td><td>${esc(c.message)}</td></tr>`).join("")}</table></details>`).join("");
  const fail = Object.values(s.gates).some((v) => v.status === "FAIL");
  if (Object.keys(s.gates).length) h += fail ? `<p class="bad">A FAIL cannot be waived. Fix the cause and run again.</p>` : `<div class="note">Stopped at <b>Gate B</b>. Nothing has been imported. Go to <b>4 · Review &amp; approve</b>.</div>`;
  return h;
}
async function showRunInto(el, name) {
  try { el.innerHTML = gatesHtml(await api("/api/run/" + name)); } catch (e) { el.innerHTML = `<p class="bad">${esc(e.message)}</p>`; }
}

// ------------------------------------------------------------ step 4: review
async function showReview(target = $("#v-out"), name = lastRun) {
  if (!name) { target.innerHTML = `<p class="muted">Run the pipeline first.</p>`; return; }
  const s = await api("/api/run/" + name);
  if (!s.template) { target.innerHTML = `<p class="muted">This run has no review packet (it stopped before Gate B).</p>`; return; }
  const t = s.approval || s.template;
  const links = [["assurance", "What was and was not checked"], ["decisions", "Decisions made"], ["summary", "Summary"], ["brief", "AI reviewer brief"]]
    .filter(([k]) => s[k]).map(([k, l]) => `<a class="btn" href="${file(s[k])}" target="_blank">${l}</a>`).join(" ");
  const opt = (v, cur) => ["ok", "defect", "unsure"].map((o) => `<option ${o === cur ? "selected" : ""}>${o}</option>`).join("");
  target.innerHTML = `
    ${s.approved ? `<div class="note ok"><b>Approved.</b> <a class="btn primary" href="${file(s.pack_zip)}?download=1">Download pack.zip</a> <a class="btn" href="${file(s.pack_json)}?download=1">pack.json</a> — import it with the practice app's Import screen.</div>` : ""}
    <p>Read <b>What was and was not checked</b> first. Then compare each item: the source on the left, what the app will show on the right. <b>Some items were corrupted on purpose</b>: marking one of them <code>ok</code> voids the approval. The reviewer must not be the profile's author.</p>
    <div class="row">${links}</div>
    <iframe class="view" src="${file(s.review)}"></iframe>
    <h3>Your verdicts</h3>
    <div class="row"><button class="btn" id="all-ok">Mark every item ok</button><span class="muted">(only after you have checked them)</span></div>
    <div class="items">${t.reviewed_items.map((r) => `<label>${esc(r.item)} <span class="muted">${esc(r.question_id)}</span><select data-item="${esc(r.item)}">${r.verdict?.startsWith("<") ? `<option value="" selected>—</option>` : ""}${opt(0, r.verdict)}</select></label>`).join("")}</div>
    <div class="grid2">
      <label>Reviewer (you, or the AI session that reviewed)<input id="a-rev" value="${esc(t.reviewer?.startsWith("<") ? "" : t.reviewer)}"></label>
      <label>Profile author<input id="a-auth" value="${esc(t.profile_author)}"></label>
      <label>Answers verified<select id="a-ans">${["none", "sampled", "full"].map((o) => `<option ${o === t.answers_verified ? "selected" : ""}>${o}</option>`).join("")}</select></label>
      ${"numerals_checked" in t ? `<label>Numbers checked (transcribed values in this run)<select id="a-num"><option value="">—</option><option ${t.numerals_checked === "full" ? "selected" : ""}>full</option></select></label>` : ""}
      <label>Decision<select id="a-dec"><option>approve</option><option>reject</option></select></label>
    </div>
    ${t.waivers.length ? `<h3>Waivers for warnings</h3>${t.waivers.map((w, i) => `<label class="muted" style="display:block;margin:6px 0"><code>${esc(w.check_id)}</code><input data-waiver="${i}" style="width:100%" placeholder="why this is acceptable" value="${esc(w.reason?.startsWith("<") ? "" : w.reason)}"></label>`).join("")}` : ""}
    <div class="row"><button class="btn primary" id="a-go">Check and approve</button></div>
    <div id="a-out"></div>`;
  $("#all-ok", target).onclick = () => target.querySelectorAll("select[data-item]").forEach((s) => (s.value = "ok"));
  $("#a-go", target).onclick = async () => {
    const a = structuredClone(s.template);
    a.decision = $("#a-dec", target).value;
    a.reviewer = $("#a-rev", target).value.trim();
    a.profile_author = $("#a-auth", target).value.trim();
    a.answers_verified = $("#a-ans", target).value;
    if ($("#a-num", target)) a.numerals_checked = $("#a-num", target).value;
    a.reviewed_items.forEach((r) => (r.verdict = target.querySelector(`select[data-item="${CSS.escape(r.item)}"]`).value));
    a.waivers.forEach((w, i) => (w.reason = target.querySelector(`[data-waiver="${i}"]`).value.trim()));
    delete a.approved_at;
    const res = await api("/api/approve", { run: name, approval: a });
    $("#a-out", target).innerHTML = `<pre class="${res.code === 0 ? "ok" : "bad"}">${esc(res.out)}</pre>`;
    if (res.code === 0) { await refresh(); showReview(target, name); }
  };
}

// ------------------------------------------------------------ a run on its own
async function openRun(name) {
  current = null; lastRun = name;
  $("#welcome").hidden = true; $("#paper").hidden = true;
  const v = $("#runview"); v.hidden = false;
  v.innerHTML = `<div class="step"><div id="rv-g"></div></div><div class="step" style="margin-top:14px"><div id="rv-r"></div></div>`;
  await showRunInto($("#rv-g"), name);
  await showReview($("#rv-r"), name);
  refresh();
}

refresh(); loadLibrary();
