"use strict";
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let me = null;

/* ---------- plumbing ---------- */
async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(path, { method, headers: body ? { "Content-Type": "application/json" } : {}, body: body ? JSON.stringify(body) : undefined });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && me) { me = null; go("#/login"); }
    const d = data.detail;
    throw new Error(Array.isArray(d) ? d.map(e => e.msg.replace(/^Value error, /, "")).join(", ") : d || "Something went wrong");
  }
  return data;
}
function toast(msg, err = false) {
  const t = document.createElement("div");
  t.className = "toast" + (err ? " err" : ""); t.textContent = msg;
  $("#toasts").append(t); setTimeout(() => t.remove(), 3200);
}
const go = h => { location.hash = h; };
const guard = fn => async (...a) => { try { return await fn(...a); } catch (e) { toast(e.message, true); } };

function avatar(name, cls = "") {
  let h = 0; for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 360;
  return `<span class="avatar ${cls}" style="background:linear-gradient(145deg,hsl(${h} 70% 62%),hsl(${(h + 40) % 360} 65% 48%))" aria-hidden="true">${esc(name.trim()[0]?.toUpperCase() || "?")}</span>`;
}
const stars = r => r ? `<span class="stars" title="${r.toFixed(1)} out of 5">${"★".repeat(Math.round(r))}${"☆".repeat(5 - Math.round(r))}</span>` : "";
const tags = (list, cls = "") => list.map(t => `<span class="tag ${cls}">${esc(t)}</span>`).join("");
const fmtCredits = n => (Math.round(n * 100) / 100).toString();

function sheet(html, onMount) {
  const root = $("#sheet-root");
  root.innerHTML = `<div class="backdrop"><div class="sheet" role="dialog" aria-modal="true">${html}</div></div>`;
  const close = () => { root.innerHTML = ""; document.removeEventListener("keydown", esc_); };
  const esc_ = e => e.key === "Escape" && close();
  document.addEventListener("keydown", esc_);
  $(".backdrop", root).addEventListener("mousedown", e => e.target.classList.contains("backdrop") && close());
  onMount?.(root, close); return close;
}

/* chip (tag) input: returns { get() } */
function chipInput(el, initial = [], placeholder = "") {
  let items = [...initial];
  const draw = () => {
    el.innerHTML = items.map((t, i) => `<span class="chip">${esc(t)}<button type="button" data-i="${i}" aria-label="Remove ${esc(t)}">×</button></span>`).join("") + `<input placeholder="${items.length ? "" : esc(placeholder)}" aria-label="${esc(placeholder)}">`;
    const input = $("input", el);
    const add = () => { const v = input.value.trim().replace(/,$/, "").trim(); if (v && !items.includes(v.toLowerCase())) items.push(v.toLowerCase()); input.value = ""; };
    input.addEventListener("keydown", e => {
      if (e.key === "Enter" || e.key === ",") { e.preventDefault(); add(); draw(); $("input", el).focus(); }
      else if (e.key === "Backspace" && !input.value && items.length) { items.pop(); draw(); $("input", el).focus(); }
    });
    input.addEventListener("blur", () => { if (input.value.trim()) { add(); draw(); } });
    el.onclick = e => { const b = e.target.closest("button[data-i]"); if (b) { items.splice(+b.dataset.i, 1); draw(); $("input", el).focus(); } else input.focus(); };
  };
  draw();
  return { get: () => { const i = $("input", el); if (i?.value.trim()) { const v = i.value.trim().toLowerCase(); if (!items.includes(v)) items.push(v); i.value = ""; } return [...items]; } };
}

/* ---------- router ---------- */
const PUBLIC = new Set(["", "#/", "#/login", "#/signup"]);
async function render() {
  const hash = location.hash;
  if (!me && !PUBLIC.has(hash)) return go("#/");
  if (me && (PUBLIC.has(hash))) return go("#/discover");
  const app = $("#app");
  window.scrollTo(0, 0);
  if (!me) {
    app.innerHTML = hash === "#/login" ? loginView() : hash === "#/signup" ? signupView() : landingView();
    if (hash === "#/login") bindLogin(); if (hash === "#/signup") bindSignup();
    return;
  }
  const [, route, arg] = hash.split("/");
  app.innerHTML = shell(route) ;
  const main = $("#main");
  main.innerHTML = `<div class="spinner" role="status" aria-label="Loading"></div>`;
  try {
    if (route === "discover") await discoverView(main);
    else if (route === "people") arg ? await personView(main, +arg) : await peopleView(main);
    else if (route === "sessions") await sessionsView(main);
    else if (route === "profile") profileView(main);
    else go("#/discover");
  } catch (e) { main.innerHTML = `<div class="empty"><div class="big">⚠️</div>${esc(e.message)}</div>`; }
}
window.addEventListener("hashchange", render);

const ICONS = {
  discover: '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5z"/>',
  people: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.6-3.6 3.2-5.5 6.5-5.5s5.9 1.9 6.5 5.5M16 4.8a3.5 3.5 0 0 1 0 6.4M18 14.8c2 .6 3.1 2.3 3.5 5.2"/>',
  sessions: '<rect x="3.5" y="5" width="17" height="15" rx="3"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
  profile: '<circle cx="12" cy="8.5" r="4"/><path d="M4.5 20.5c.8-4 3.7-6 7.5-6s6.7 2 7.5 6"/>',
};
const LABELS = { discover: "Discover", people: "People", sessions: "Sessions", profile: "Profile" };
function shell(route) {
  const nav = Object.keys(ICONS).map(k => `<a href="#/${k}" ${route === k ? 'aria-current="page"' : ""}><svg viewBox="0 0 24 24">${ICONS[k]}</svg>${LABELS[k]}</a>`).join("");
  return `<div class="shell"><aside class="sidebar"><div class="brand"><span class="brand-mark">⇄</span>SkillSwap</div>
    <nav class="nav" aria-label="Main">${nav}</nav>
    <a class="me" href="#/profile" style="color:inherit">${avatar(me.name, "sm")}<div><b>${esc(me.name)}</b><span>${fmtCredits(me.credits)} credits</span></div></a></aside>
    <main id="main"></main></div>`;
}

/* ---------- landing & auth ---------- */
function landingView() {
  return `<div class="landing">
    <div class="topbar"><div class="brand" style="padding:0"><span class="brand-mark">⇄</span>SkillSwap</div>
      <div><a class="btn plain" href="#/login">Sign in</a> <a class="btn primary" href="#/signup">Get started</a></div></div>
    <section class="hero"><h1>Trade skills,<br><em>not cash.</em></h1>
      <p>Teach what you know, learn what you need. SkillSwap finds the people who complete your side hustle, even when it takes three of you to close the loop.</p>
      <div class="cta"><a class="btn primary big" href="#/signup">Create your free account</a><a class="btn big" href="#/login">Sign in</a></div>
      <div class="card loop-demo" aria-label="Example of a three-way skill loop">
        <p class="label">EXAMPLE: A THREE-WAY LOOP</p>
        <div class="demo-step">${avatar("Ada", "sm")} <b>Ada</b> teaches logo design <span class="arrow">→</span> ${avatar("Carla", "sm")} <b>Carla</b></div>
        <div class="demo-step">${avatar("Carla", "sm")} <b>Carla</b> teaches Spanish <span class="arrow">→</span> ${avatar("Ben", "sm")} <b>Ben</b></div>
        <div class="demo-step">${avatar("Ben", "sm")} <b>Ben</b> teaches Python <span class="arrow">→</span> ${avatar("Ada", "sm")} <b>Ada</b></div></div></section>
    <section class="features">
      <div class="card feature"><div class="ico">🔁</div><h3>Direct swaps and loops</h3><p class="muted">A graph search finds two-way swaps and longer chains no one would spot by hand.</p></div>
      <div class="card feature"><div class="ico">⏱️</div><h3>Time credits</h3><p class="muted">No match yet? Earn hours by teaching and spend them with anyone on the network.</p></div>
      <div class="card feature"><div class="ico">🔒</div><h3>Private by design</h3><p class="muted">Optional AI runs on an open-weight model on your own machine. Your profile stays yours.</p></div>
    </section></div>`;
}

function authShell(inner) { return `<div class="auth-wrap"><div class="card auth">${inner}</div></div>`; }
const field = (label, input, hint = "") => `<label class="field"><span>${label}</span>${input}${hint ? `<p class="hint">${hint}</p>` : ""}</label>`;

function loginView() {
  return authShell(`<a class="small" href="#/">‹ Back</a><h1 style="margin-top:14px">Welcome back</h1><p class="sub">Sign in to continue swapping.</p>
    <form id="login" novalidate>${field("Email", '<input class="input" name="email" type="email" autocomplete="email" required>')}
    ${field("Password", '<input class="input" name="password" type="password" autocomplete="current-password" required>')}
    <p class="error" id="err" role="alert"></p><button class="btn primary big">Sign in</button></form>
    <p class="alt">New here? <a href="#/signup">Create an account</a></p>`);
}
function bindLogin() {
  $("#login").addEventListener("submit", async e => {
    e.preventDefault(); const f = new FormData(e.target), btn = $("button", e.target);
    btn.disabled = true; $("#err").textContent = "";
    try { me = await api("/auth/login", { method: "POST", body: { email: f.get("email"), password: f.get("password") } }); go("#/discover"); }
    catch (err) { $("#err").textContent = err.message; btn.disabled = false; }
  });
}

let draft = { name: "", email: "", password: "" };
function signupView(step = 1) {
  const dots = `<div class="steps-dots" aria-hidden="true"><i class="on"></i><i class="${step === 2 ? "on" : ""}"></i></div>`;
  if (step === 1) return authShell(`${dots}<a class="small" href="#/">‹ Back</a><h1 style="margin-top:14px">Create your account</h1><p class="sub">Step 1 of 2. It takes under a minute.</p>
    <form id="s1" novalidate>${field("Name", `<input class="input" name="name" autocomplete="name" value="${esc(draft.name)}" required>`)}
    ${field("Email", `<input class="input" name="email" type="email" autocomplete="email" value="${esc(draft.email)}" required>`)}
    ${field("Password", '<input class="input" name="password" type="password" autocomplete="new-password" minlength="8" required>', "At least 8 characters.")}
    <p class="error" id="err" role="alert"></p><button class="btn primary big">Continue</button></form>
    <p class="alt">Already have an account? <a href="#/login">Sign in</a></p>`);
  return authShell(`${dots}<h1>What's your side hustle?</h1><p class="sub">Step 2 of 2. This is how we find your matches. You can change it later.</p>
    <form id="s2" novalidate>${field("I can teach", '<div class="chips" id="offers"></div>', "Type a skill and press Return.")}
    ${field("I want to learn", '<div class="chips" id="wants"></div>')}
    ${field("About you (optional)", '<textarea class="input" name="bio" maxlength="300" placeholder="One line about what you are building"></textarea>')}
    <p class="error" id="err" role="alert"></p><button class="btn primary big">Create account</button>
    <p class="alt"><a href="#" id="back">‹ Back</a></p></form>`);
}
function bindSignup() {
  const mount = $("#app");
  $("#s1").addEventListener("submit", e => {
    e.preventDefault(); const f = new FormData(e.target);
    draft = { name: f.get("name").trim(), email: f.get("email").trim(), password: f.get("password") };
    const bad = !draft.name ? "Enter your name." : !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(draft.email) ? "Enter a valid email address." : draft.password.length < 8 ? "Password must be at least 8 characters." : "";
    if (bad) return void ($("#err").textContent = bad);
    mount.innerHTML = signupView(2);
    const offers = chipInput($("#offers"), [], "e.g. logo design, python"), wants = chipInput($("#wants"), [], "e.g. spanish, video editing");
    $("#back").onclick = ev => { ev.preventDefault(); mount.innerHTML = signupView(1); bindSignup(); };
    $("#s2").addEventListener("submit", async ev => {
      ev.preventDefault(); const btn = $("button.primary", ev.target); btn.disabled = true; $("#err").textContent = "";
      try {
        me = await api("/auth/signup", { method: "POST", body: { ...draft, bio: new FormData(ev.target).get("bio"), offers: offers.get(), wants: wants.get() } });
        draft = { name: "", email: "", password: "" }; toast("Welcome to SkillSwap! You start with 2 free credits."); go("#/discover");
      } catch (err) { $("#err").textContent = err.message; btn.disabled = false; }
    });
  });
}

/* ---------- discover ---------- */
async function discoverView(main) {
  const [m, credit] = await Promise.all([api("/me/matches"), api("/me/credit-options")]);
  const noSkills = !me.offers.length && !me.wants.length;
  const swapBtns = (step) => step.skills.map(s => `<button class="btn primary" data-act="book" data-teacher="${step.teacher_id}" data-skill="${esc(s)}" data-swap="1">Book ${esc(s)}</button>`).join("");
  const planBtn = step => `<button class="btn" data-act="plan" data-teacher="${step.teacher_id}" data-learner="${step.learner_id}" data-skill="${esc(step.skills[0])}">Starter plan</button>`;

  const directCard = c => {
    const inn = c.steps.find(s => s.learner_id === me.id), out = c.steps.find(s => s.teacher_id === me.id);
    return `<div class="row"><div class="avatar-pair">${avatar(me.name)}${avatar(inn.teacher)}</div><div class="grow">
      <h3>You ⇄ ${esc(inn.teacher)}</h3>
      <div class="step small"><b>${esc(inn.teacher)}</b> teaches you ${tags(inn.skills, "accent")}</div>
      <div class="step small">You teach <b>${esc(inn.teacher)}</b> ${tags(out.skills)}</div><div class="plan-slot"></div></div>
      <div class="actions">${planBtn(inn)}${swapBtns(inn)}</div></div>`;
  };
  const loopCard = c => {
    const inn = c.steps.find(s => s.learner_id === me.id);
    return `<div class="row"><div class="avatar-pair">${c.steps.slice(0, 4).map(s => avatar(s.teacher)).join("")}</div><div class="grow">
      <h3>${c.size}-way loop</h3>
      ${c.steps.map(s => `<div class="step small"><b>${esc(s.teacher_id === me.id ? "You" : s.teacher)}</b> teaches <b>${esc(s.learner_id === me.id ? "you" : s.learner)}</b> ${tags(s.skills, s.learner_id === me.id ? "accent" : "")}</div>`).join("")}<div class="plan-slot"></div></div>
      <div class="actions">${planBtn(inn)}${swapBtns(inn)}</div></div>`;
  };
  const creditRow = t => `<div class="row click" data-act="person" data-id="${t.teacher_id}">${avatar(t.name)}<div class="grow"><h3>${esc(t.name)}</h3><div>${tags(t.skills, "accent")}</div></div>
    <div class="actions">${t.skills.map(s => `<button class="btn" data-act="book" data-teacher="${t.teacher_id}" data-skill="${esc(s)}" data-swap="">Book ${esc(s)} · 1 credit</button>`).join("")}</div></div>`;

  const section = (title, items, render, emptyText) => `<div class="group-title">${title}</div><div class="card list">${items.length ? items.map(render).join("") : `<div class="empty">${emptyText}</div>`}</div>`;
  main.innerHTML = `<div class="page-head"><div><h1>Discover</h1><p class="muted">People who can teach you what you want, and need what you offer.</p></div></div>
    <div class="stat-row"><div class="card stat"><b>${m.direct.length}</b><span>Direct swaps</span></div><div class="card stat"><b>${m.loops.length}</b><span>Loops</span></div><div class="card stat"><b>${fmtCredits(credit.balance)}</b><span>Credits</span></div></div>
    ${noSkills ? `<div class="card pad" style="margin-top:20px"><h3>Add your skills to get matches</h3><p class="muted" style="margin:4px 0 12px">Matches appear as soon as you list what you teach and want to learn.</p><a class="btn primary" href="#/profile">Edit profile</a></div>` : ""}
    ${section("Direct swaps", m.direct, directCard, "No two-way swaps yet. Try the loops and credits below.")}
    ${section("Loops", m.loops, loopCard, "No loops yet. They appear as more people join.")}
    ${section("Learn with credits", credit.teachers, creditRow, "Nobody teaches what you want yet.")}`;
}

/* ---------- people ---------- */
async function peopleView(main) {
  const users = (await api("/users")).filter(u => u.id !== me.id);
  const rows = q => users.filter(u => !q || [u.name, u.bio, ...u.offers, ...u.wants].join(" ").toLowerCase().includes(q.toLowerCase()))
    .map(u => `<div class="row click" data-act="person" data-id="${u.id}">${avatar(u.name)}<div class="grow"><h3>${esc(u.name)} ${stars(u.rating)}</h3>
      <div class="small muted">${esc(u.bio)}</div><div>${tags(u.offers, "accent")}</div></div><span class="chev">›</span></div>`).join("")
    || `<div class="empty"><div class="big">🔍</div>No one matches that search.</div>`;
  main.innerHTML = `<div class="page-head"><div><h1>People</h1><p class="muted">${users.length} ${users.length === 1 ? "person" : "people"} on SkillSwap</p></div>
    <input class="input" id="q" type="search" placeholder="Search skills or names" style="max-width:260px" aria-label="Search"></div><div class="card list" id="plist">${rows("")}</div>`;
  $("#q").addEventListener("input", e => { $("#plist").innerHTML = rows(e.target.value); });
}
async function personView(main, id) {
  const u = await api(`/users/${id}`);
  main.innerHTML = `<a href="#/people" class="small">‹ People</a>
    <div class="card pad" style="margin-top:12px;display:flex;gap:18px;align-items:center;flex-wrap:wrap">${avatar(u.name, "lg")}<div><h1>${esc(u.name)}</h1><p class="muted">${esc(u.bio)}</p>
    <p>${stars(u.rating)} <span class="small muted">${u.reviews ? `${u.reviews} review${u.reviews > 1 ? "s" : ""}` : "No reviews yet"}</span></p></div></div>
    <div class="group-title">Can teach</div><div class="card list">${u.offers.map(s => `<div class="row"><div class="grow"><h3>${esc(s)}</h3></div><button class="btn primary" data-act="book" data-teacher="${u.id}" data-skill="${esc(s)}" data-swap="">Book 1 hr · 1 credit</button></div>`).join("") || '<div class="empty">Nothing listed yet.</div>'}</div>
    <div class="group-title">Wants to learn</div><div class="card pad">${tags(u.wants) || '<span class="muted">Nothing listed yet.</span>'}</div>`;
}

/* ---------- sessions ---------- */
let sessionTab = "upcoming";
async function sessionsView(main) {
  const all = await api("/me/sessions");
  const list = all.filter(s => (sessionTab === "upcoming") === (s.status === "scheduled"));
  const row = s => {
    const learner = s.learner_id === me.id, other = learner ? s.teacher : s.learner;
    let act = "";
    if (s.status === "scheduled") act = (s.swap || learner) ? `<button class="btn primary" data-act="complete" data-id="${s.id}">Mark complete</button>` : `<span class="small muted">Waiting for ${esc(s.learner)} to confirm</span>`;
    else act = s.reviewed ? `<span class="small muted">✓ Reviewed</span>` : `<button class="btn" data-act="review" data-id="${s.id}" data-who="${esc(other)}">Leave review</button>`;
    return `<div class="row">${avatar(other)}<div class="grow"><h3>${learner ? `Learn ${esc(s.skill)} from ${esc(other)}` : `Teach ${esc(s.skill)} to ${esc(other)}`}</h3>
      <div class="small muted">${s.hours} hr · ${s.swap ? "Skill swap" : learner ? `${s.hours} credit${s.hours === 1 ? "" : "s"} to pay` : `${s.hours} credit${s.hours === 1 ? "" : "s"} to earn`}</div></div><div class="actions">${act}</div></div>`;
  };
  main.innerHTML = `<div class="page-head"><div><h1>Sessions</h1><p class="muted">Complete a session to move credits and unlock reviews.</p></div>
    <div class="segmented" role="group" aria-label="Filter"><button aria-pressed="${sessionTab === "upcoming"}" data-act="tab" data-tab="upcoming">Upcoming</button><button aria-pressed="${sessionTab === "done"}" data-act="tab" data-tab="done">Completed</button></div></div>
    <div class="card list">${list.map(row).join("") || `<div class="empty"><div class="big">${sessionTab === "upcoming" ? "📅" : "✅"}</div>${sessionTab === "upcoming" ? "Nothing booked. Find a match in Discover." : "No completed sessions yet."}</div>`}</div>`;
}

/* ---------- profile ---------- */
function profileView(main) {
  main.innerHTML = `<div class="page-head"><h1>Profile</h1></div>
    <div class="card pad" style="display:flex;gap:18px;align-items:center;flex-wrap:wrap">${avatar(me.name, "lg")}<div><h2>${esc(me.name)}</h2><p class="muted">${esc(me.email)}</p>
      <p>${stars(me.rating)} <span class="small muted">${me.reviews ? `${me.reviews} review${me.reviews > 1 ? "s" : ""}` : "No reviews yet"}</span></p></div>
      <div class="card stat" style="margin-left:auto"><b>${fmtCredits(me.credits)}</b><span>Credits</span></div></div>
    <div class="group-title">Edit</div><form class="card pad" id="pf" novalidate>
      ${field("Name", `<input class="input" name="name" value="${esc(me.name)}" required>`)}
      ${field("About you", `<textarea class="input" name="bio" maxlength="300">${esc(me.bio)}</textarea>`)}
      ${field("I can teach", '<div class="chips" id="offers"></div>')}${field("I want to learn", '<div class="chips" id="wants"></div>')}
      <div style="display:flex;gap:10px;justify-content:space-between"><button type="button" class="btn danger" data-act="logout">Sign out</button><button class="btn primary">Save changes</button></div></form>`;
  const offers = chipInput($("#offers"), me.offers, "Add a skill"), wants = chipInput($("#wants"), me.wants, "Add a skill");
  $("#pf").addEventListener("submit", guard(async e => {
    e.preventDefault(); const f = new FormData(e.target);
    me = await api("/me", { method: "PATCH", body: { name: f.get("name"), bio: f.get("bio"), offers: offers.get(), wants: wants.get() } });
    toast("Profile saved"); profileView(main);
  }));
}

/* ---------- actions (event delegation) ---------- */
const actions = {
  tab: el => { sessionTab = el.dataset.tab; render(); },
  person: el => go(`#/people/${el.dataset.id}`),
  logout: guard(async () => { await api("/auth/logout", { method: "POST" }); me = null; go("#/"); }),
  book: guard(async el => {
    const swap = !!el.dataset.swap;
    await api("/sessions", { method: "POST", body: { teacher_id: +el.dataset.teacher, skill: el.dataset.skill, hours: 1, swap } });
    toast(swap ? "Swap booked. Find it under Sessions." : "Session booked. Credits move when you mark it complete."); go("#/sessions");
  }),
  complete: guard(async el => {
    await api(`/sessions/${el.dataset.id}/complete`, { method: "POST" });
    me = await api("/me"); toast("Session completed"); render();
  }),
  plan: guard(async el => {
    const slot = $(".plan-slot", el.closest(".row")); el.disabled = true; slot.innerHTML = `<div class="plan muted">Writing a plan…</div>`;
    const p = await api(`/swap-plan?teacher_id=${el.dataset.teacher}&learner_id=${el.dataset.learner}&skill=${encodeURIComponent(el.dataset.skill)}`);
    slot.innerHTML = `<div class="plan">${esc(p.plan)} <span class="muted">· ${p.source === "model" ? "written by your local model" : "template"}</span></div>`;
  }),
  review: el => {
    let rating = 0;
    sheet(`<h2>Review ${esc(el.dataset.who)}</h2><p class="muted small">How was your session?</p>
      <div class="star-input" role="radiogroup" aria-label="Rating">${[1, 2, 3, 4, 5].map(n => `<button type="button" role="radio" aria-checked="false" aria-label="${n} star${n > 1 ? "s" : ""}" data-n="${n}">★</button>`).join("")}</div>
      <textarea class="input" id="cmt" maxlength="500" placeholder="Add a comment (optional)"></textarea>
      <div class="btns"><button class="btn" id="cancel">Cancel</button><button class="btn primary" id="send" disabled>Submit</button></div>`, (root, close) => {
      $(".star-input", root).onclick = e => { const b = e.target.closest("button"); if (!b) return; rating = +b.dataset.n;
        root.querySelectorAll(".star-input button").forEach(x => { x.classList.toggle("on", +x.dataset.n <= rating); x.setAttribute("aria-checked", +x.dataset.n === rating); }); $("#send", root).disabled = false; };
      $("#cancel", root).onclick = close;
      $("#send", root).onclick = guard(async () => { await api(`/sessions/${el.dataset.id}/review`, { method: "POST", body: { rating, comment: $("#cmt", root).value } }); close(); toast("Thanks for the review"); render(); });
    });
  },
};
document.addEventListener("click", e => {
  const el = e.target.closest("[data-act]");
  if (!el || (el.dataset.act === "person" && e.target.closest("button"))) return;
  actions[el.dataset.act]?.(el);
});

/* ---------- boot ---------- */
(async () => { try { me = await api("/me"); } catch { me = null; } render(); })();
