const $ = id => document.getElementById(id);

const PLATFORMS = [
  { id: 'twitch', on: 'onTw', name: 'nameTw', panel: 'pTw', label: 'Twitch' },
  { id: 'kick', on: 'onKk', name: 'nameKk', panel: 'pKk', label: 'Kick' },
  { id: 'tiktok', on: 'onTt', name: 'nameTt', panel: 'pTt', label: 'TikTok' },
  { id: 'youtube', on: 'onYt', name: 'nameYt', panel: 'pYt', label: 'YouTube' },
].map(p => ({ ...p, onEl: $(p.on), nameEl: $(p.name), panelEl: $(p.panel) }));

function estado() {
  const s = {
    label: $('label').value,
    position: $('position').value,
    align: $('align').value,
    animation: $('animation').value,
    duration: parseFloat($('duration').value) || 6,
    fps: 30
  };
  for (const p of PLATFORMS) s[p.id] = p.onEl.checked ? p.nameEl.value.trim() : null;
  return s;
}

function activas() {
  return PLATFORMS.filter(p => p.onEl.checked);
}

function validar(s) {
  const on = activas();
  if (on.length === 0) return 'Activa al menos una plataforma.';
  if (on.length > 2) return 'Como máximo dos plataformas.';
  for (const p of on) {
    if (!s[p.id]) return `Falta el nombre de ${p.label}.`;
  }
  return '';
}

let tPrev;
function refrescar() {
  const on = activas();
  const atLimite = on.length >= 2;
  for (const p of PLATFORMS) {
    p.panelEl.dataset.on = p.onEl.checked ? '1' : '0';
    p.nameEl.disabled = !p.onEl.checked;
    p.onEl.disabled = atLimite && !p.onEl.checked;
  }

  const s = estado();
  const err = validar(s);
  $('warn').textContent = err;
  $('go').disabled = !!err;
  if (err) {
    $('prev').removeAttribute('src');
    $('prev').style.display = 'none';
    return;
  }

  clearTimeout(tPrev);
  tPrev = setTimeout(() => {
    const q = new URLSearchParams();
    for (const p of PLATFORMS) if (s[p.id]) q.set(p.id, s[p.id]);
    q.set('label', s.label);
    q.set('position', s.position);
    q.set('align', s.align);
    q.set('animation', s.animation);
    q.set('animate', '1');
    $('prev').src = '/preview.svg?' + q.toString();
    $('prev').style.display = '';
    $('vid').style.display = 'none';
  }, 220);
}

for (const p of PLATFORMS) {
  p.onEl.addEventListener('change', refrescar);
  p.nameEl.addEventListener('input', refrescar);
}
['label', 'position', 'align', 'animation', 'duration'].forEach(id => {
  $(id).addEventListener('input', refrescar);
  $(id).addEventListener('change', refrescar);
});

document.querySelectorAll('.bgpick button').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('.bgpick button').forEach(x => x.setAttribute('aria-pressed', 'false'));
    b.setAttribute('aria-pressed', 'true');
    $('bg').className = 'bg ' + b.dataset.bg;
  });
});

$('go').addEventListener('click', async () => {
  const s = estado();
  const err = validar(s);
  if (err) { $('warn').textContent = err; return; }

  const btn = $('go');
  btn.disabled = true;
  $('dl').style.display = 'none';
  const t0 = Date.now();
  const tick = setInterval(() => {
    $('status').textContent = 'Renderizando fotogramas… ' + ((Date.now() - t0) / 1000).toFixed(0) + ' s';
  }, 500);

  try {
    const r = await fetch('/render', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(s)
    });
    if (!r.ok) {
      const d = await r.json().catch(() => ({ detail: 'Error desconocido' }));
      throw new Error(d.detail || r.statusText);
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const v = $('vid');
    v.src = url; v.style.display = ''; $('prev').style.display = 'none';
    const primerNombre = activas().map(p => s[p.id]).find(Boolean);
    const dl = $('dl');
    dl.href = url;
    dl.download = 'overlay-' + primerNombre.toLowerCase().replace(/[^a-z0-9._-]+/g, '-') + '.webm';
    dl.style.display = 'inline-block';
    $('status').textContent = 'Listo · ' + (blob.size / 1024).toFixed(0) + ' KB · ' +
                              ((Date.now() - t0) / 1000).toFixed(1) + ' s';
  } catch (e) {
    $('status').textContent = 'Error: ' + e.message;
  } finally {
    clearInterval(tick);
    btn.disabled = false;
  }
});

refrescar();
