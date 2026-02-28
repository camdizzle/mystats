const $ = (q) => document.querySelector(q);
const $$ = (q) => Array.from(document.querySelectorAll(q));

let settings = {};

function setStatus(msg, ok = true) {
  const el = $('#status');
  if (!el) return;
  el.style.color = ok ? '#84f0b7' : '#ff9c9c';
  el.textContent = msg;
}

function activateTab(id) {
  $$('.tab').forEach((btn) => btn.classList.toggle('active', btn.dataset.tab === id));
  $$('.panel').forEach((panel) => panel.classList.toggle('active', panel.id === `panel-${id}`));
  $('#tab-title').textContent = $(`.tab[data-tab="${id}"]`)?.textContent || id;
}

function fillInputs() {
  $$('input[data-key]').forEach((input) => {
    input.value = settings[input.dataset.key] ?? '';
  });
}

function collectInputs() {
  const next = {};
  $$('input[data-key]').forEach((input) => {
    next[input.dataset.key] = input.value;
  });
  return next;
}

async function loadSettings() {
  const resp = await fetch('/api/settings', { cache: 'no-store' });
  const payload = await resp.json();
  settings = payload.settings || {};
  fillInputs();
  setStatus('Settings loaded.');
}

async function saveSettings() {
  const resp = await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(collectInputs()),
  });
  if (!resp.ok) {
    setStatus('Save failed.', false);
    return;
  }
  const payload = await resp.json();
  settings = payload.settings || {};
  fillInputs();
  setStatus('Settings saved. Restart app if needed for some values.');
}

$$('.tab').forEach((btn) => btn.addEventListener('click', () => activateTab(btn.dataset.tab)));
$('#refresh').addEventListener('click', () => loadSettings().catch(() => setStatus('Load failed.', false)));
$('#save').addEventListener('click', () => saveSettings().catch(() => setStatus('Save failed.', false)));

loadSettings().catch(() => setStatus('Load failed.', false));
