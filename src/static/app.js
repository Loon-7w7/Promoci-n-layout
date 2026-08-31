const $ = id => document.getElementById(id);
const onTw = $('onTw'), onKk = $('onKk'), nameTw = $('nameTw'), nameKk = $('nameKk');
let kickTocado = false; // mientras no lo edites a mano, copia el nombre de Twitch

function estado() {
  return {
    twitch: onTw.checked ? nameTw.value.trim() : null,
    kick:   onKk.checked ? nameKk.value.trim() : null,
    label:  $('label').value,
    position: $('position').value,
    align: $('align').value,
    animation: $('animation').value,
    duration: parseFloat($('duration').value) || 6,
    fps: 30
  };
}

function validar(s) {
  if (!onTw.checked && !onKk.checked) return 'Activa al menos una plataforma.';
  if (onTw.checked && !s.twitch) return 'Falta el nombre de Twitch.';
  if (onKk.checked && !s.kick) return 'Falta el nombre de Kick.';
  return '';
}

let tPrev;
function refrescar() {
  $('pTw').dataset.on = onTw.checked ? '1' : '0';
  $('pKk').dataset.on = onKk.checked ? '1' : '0';
  nameTw.disabled = !onTw.checked;
  nameKk.disabled = !onKk.checked;

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
    if (s.twitch) q.set('twitch', s.twitch);
    if (s.kick) q.set('kick', s.kick);
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

// si Kick no se ha tocado a mano, copia el nombre de Twitch
nameTw.addEventListener('input', () => {
  if (!kickTocado) nameKk.value = nameTw.value;
  refrescar();
});
nameKk.addEventListener('input', () => { kickTocado = nameKk.value.trim() !== ''; refrescar(); });
['onTw','onKk','label','position','align','animation','duration'].forEach(id => {
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
    const dl = $('dl');
    dl.href = url;
    dl.download = 'overlay-' + ((s.twitch || s.kick).toLowerCase().replace(/[^a-z0-9._-]+/g, '-')) + '.webm';
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
