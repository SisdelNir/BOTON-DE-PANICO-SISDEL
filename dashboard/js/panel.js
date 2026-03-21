/**
 * Panel Central JS — Botón de Pánico SISDEL
 * Scoped por institución desde sessionStorage
 */

const API = (window.location.hostname === 'localhost' || window.location.protocol === 'file:') ? 'http://localhost:8000' : 'https://boton-de-panico-sisdel.onrender.com';  // Local o Render
let INST  = null;
let mapaL = null;
let marcadores = {};
let alertaActual = null;
let filtro = 'todas';
let _alertasVistas = new Set();   // IDs de emergencias ya vistas
let _audioCtx = null;             // Web Audio para alarma

// ── INIT ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    if (sessionStorage.getItem('sisdel_tipo') !== 'institucion') {
        window.location.href = 'index.html'; return;
    }
    INST = JSON.parse(sessionStorage.getItem('sisdel_inst'));
    document.getElementById('inst-name-label').textContent = INST.nombre_institucion;
    document.title = `🚨 ${INST.nombre_institucion} — Panel SISDEL`;

    iniciarReloj();
    iniciarMapa();
    pedirPermisoNotificacion();
    cargarAlertas();
    cargarVecinos();
    // Refresco cada 5 segundos
    setInterval(() => { cargarAlertas(); }, 5000);
    // Keep-alive: ping a Render cada 4 minutos para evitar que duerma
    setInterval(() => { fetch(`${API}/health`).catch(()=>{}); }, 4 * 60 * 1000);
});


function logout() { sessionStorage.clear(); window.location.href = 'index.html'; }

function abrirRegistroVecino() {
    const base = window.location.pathname.replace('panel.html','');
    const url = `${base}vecino.html?inst=${INST.id_institucion}&admin=1`;
    window.open(url, '_blank');
}

// ── RELOJ ─────────────────────────────────────────
function iniciarReloj() {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone; // zona del dispositivo
    const tick = () => {
        document.getElementById('clock').textContent =
            new Date().toLocaleTimeString([], { hour12: false, timeZone: tz });
    };
    tick(); setInterval(tick, 1000);
}

// ── MAPA ──────────────────────────────────────────
function iniciarMapa() {
    // Centro: Guatemala (ajusta según tu país)
    mapaL = L.map('mapa').setView([14.6349, -90.5069], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        {attribution:'© OpenStreetMap'}).addTo(mapaL);
}
function centrarMapa() { if(mapaL) mapaL.setView([14.6349,-90.5069],12); }

function abrirMapa() {
    document.getElementById('modal-mapa').style.display='flex';
    if(mapaL) {
        setTimeout(() => {
            mapaL.invalidateSize();
            centrarMapa();
        }, 100);
    }
}
function cerrarMapa(e) {
    if (e && e.target!==document.getElementById('modal-mapa')) return;
    document.getElementById('modal-mapa').style.display='none';
}

function verMapaRapido(lat, lon) {
    document.getElementById('modal-mapa').style.display='flex';
    if(mapaL) {
        setTimeout(() => {
            mapaL.invalidateSize();
            mapaL.setView([lat, lon], 16);
        }, 100);
    }
}

async function avisarFamiliares(id_vecino, nombre_vecino, locUrl) {
    if (!id_vecino) { alert('No hay ID de vecino válido en esta emergencia.'); return; }
    
    document.getElementById('avisar-body').innerHTML = '<p style="color:#6b7294;font-size:.85rem;text-align:center;">Buscando contactos...</p>';
    document.getElementById('modal-avisar').style.display='flex';
    
    try {
        const res = await fetch(`${API}/api/vecinos/${id_vecino}/contactos`);
        const contactos = await res.json();
        
        if (!contactos || !contactos.length) {
            document.getElementById('avisar-body').innerHTML = '<p style="color:#ff3b3b;font-size:.85rem;text-align:center;">Este vecino no tiene familiares registrados.</p>';
            return;
        }
        
        const textoWA = `🚨 INFO DE CENTRAL SISDEL 🚨\n\nHemos recibido una Alerta de Pánico de *${nombre_vecino}*.\n📍 Ubicación: ${locUrl}\n\nNuestras unidades están siendo notificadas para verificar la situación.`;
        
        document.getElementById('avisar-body').innerHTML = contactos.map(c => {
            const num = c.telefono.replace(/\D/g, '');
            const urlWeb = `https://wa.me/${num}?text=${encodeURIComponent(textoWA)}`;
            
            return `
                <a href="${urlWeb}" target="_blank" rel="noopener"
                   style="display:flex; align-items:center; justify-content:center; gap:.5rem;
                          background:#25d366; color:#fff; padding:.6rem;
                          border-radius:8px; font-weight:700; font-size:.85rem; text-decoration:none;">
                   <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
                        <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/>
                        <path d="M12 0C5.373 0 0 5.373 0 12c0 2.127.558 4.126 1.533 5.857L.057 23.704a.75.75 0 00.92.92l5.847-1.476A11.943 11.943 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 21.75a9.693 9.693 0 01-4.944-1.355l-.354-.21-3.668.926.944-3.565-.23-.366A9.693 9.693 0 012.25 12C2.25 6.615 6.615 2.25 12 2.25S21.75 6.615 21.75 12 17.385 21.75 12 21.75z"/>
                    </svg>
                   Avisar a ${c.nombre || c.telefono}
                </a>
            `;
        }).join('');
        
    } catch {
        document.getElementById('avisar-body').innerHTML = '<p style="color:#ff3b3b;font-size:.85rem;text-align:center;">Error de conexión.</p>';
    }
}

function cerrarAvisar(e) {
    if (e && e.target!==document.getElementById('modal-avisar')) return;
    document.getElementById('modal-avisar').style.display='none';
}

function ponerMarcador(e) {
    if (!mapaL || !e.gps_latitud || !e.gps_longitud) return;
    if (marcadores[e.id_emergencia]) mapaL.removeLayer(marcadores[e.id_emergencia]);
    const c = e.estatus==='ACTIVA'?'#ff3b3b':e.estatus==='EN_CAMINO'?'#ff8c00':'#00d68f';
    const icon = L.divIcon({
        html:`<div style="background:${c};width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 8px ${c}"></div>`,
        iconSize:[14,14], className:''
    });
    marcadores[e.id_emergencia] = L.marker([e.gps_latitud,e.gps_longitud],{icon})
        .bindPopup(`<b>🚨 ${e.nombre_vecino}</b><br>📱 ${e.telefono_vecino}<br>📍 ${e.direccion_aproximada||'Sin coords'}`)
        .addTo(mapaL);
}

// ── ALARMA SONORA ─────────────────────────────────
function pedirPermisoNotificacion() {
    if ('Notification' in window && Notification.permission === 'default')
        Notification.requestPermission();
}

function sonarAlarma() {
    try {
        if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        [0, 0.3, 0.6].forEach(t => {
            const osc = _audioCtx.createOscillator();
            const gain = _audioCtx.createGain();
            osc.connect(gain); gain.connect(_audioCtx.destination);
            osc.type = 'square';
            osc.frequency.setValueAtTime(880, _audioCtx.currentTime + t);
            gain.gain.setValueAtTime(0.4, _audioCtx.currentTime + t);
            gain.gain.exponentialRampToValueAtTime(0.001, _audioCtx.currentTime + t + 0.25);
            osc.start(_audioCtx.currentTime + t);
            osc.stop(_audioCtx.currentTime + t + 0.25);
        });
    } catch {}
}

function notificarNuevaEmergencia(nombre) {
    sonarAlarma();
    let n = 0, orig = document.title;
    const iv = setInterval(() => {
        document.title = n++ % 2 === 0 ? '🚨 ¡NUEVA ALERTA!' : orig;
        if (n >= 12) { clearInterval(iv); document.title = orig; }
    }, 500);
    if ('Notification' in window && Notification.permission === 'granted')
        new Notification('🚨 ALERTA DE PÁNICO', { body: nombre, icon: '/favicon.ico' });
}

function setConexion(ok) {
    const el = document.getElementById('conexion-status');
    if (!el) return;
    el.textContent = ok ? '🟢 Conectado' : '🔴 Sin conexión';
    el.style.color  = ok ? '#00d68f' : '#ff3b3b';
}

// ── ALERTAS ───────────────────────────────────────
async function cargarAlertas() {
    try {
        const res = await fetch(`${API}/api/emergencias/${INST.id_institucion}`);
        const alertas = await res.json();

        // Detectar nuevas ACTIVAS no vistas antes
        const nuevas = alertas.filter(a => a.estatus === 'ACTIVA' && !_alertasVistas.has(a.id_emergencia));
        if (nuevas.length > 0 && _alertasVistas.size > 0) {
            nuevas.forEach(a => notificarNuevaEmergencia(a.nombre_vecino));
        }
        alertas.forEach(a => _alertasVistas.add(a.id_emergencia));

        renderAlertas(alertas);
        alertas.forEach(ponerMarcador);
        actualizarStats(alertas);
        setConexion(true);
    } catch { setConexion(false); }
}

function actualizarStats(alertas) {
    document.getElementById('sp-activas').textContent = alertas.filter(a=>a.estatus==='ACTIVA').length;
    document.getElementById('sp-camino').textContent  = alertas.filter(a=>a.estatus==='EN_CAMINO').length;
    document.getElementById('sp-atend').textContent   = alertas.filter(a=>a.estatus==='ATENDIDA').length;
}

function setFiltro(f,btn) {
    filtro=f;
    document.querySelectorAll('.ftab').forEach(t=>t.classList.remove('active'));
    btn.classList.add('active');
    cargarAlertas();
}

function renderAlertas(alertas) {
    let lista = filtro==='todas' ? alertas : alertas.filter(a=>a.estatus===filtro);
    const tbody = document.getElementById('alertas-tbody');

    if (!lista.length) {
        tbody.innerHTML=`<tr><td colspan="9"><div class="empty-state"><span style="font-size:2rem">🛡️</span><p>Sin emergencias ${filtro!=='todas'?'con este estado':''}</p></div></td></tr>`;
        return;
    }

    tbody.innerHTML = lista.map((a,i) => {
        const rowCls = a.estatus==='ACTIVA'?'row-activa':a.estatus==='EN_CAMINO'?'row-camino':a.estatus==='ATENDIDA'?'row-atendida':'';
        const tz   = Intl.DateTimeFormat().resolvedOptions().timeZone;
        const hora = new Date(a.fecha_creacion + 'Z').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: tz });
        const gps    = a.gps_latitud ? `${a.gps_latitud.toFixed(4)},${a.gps_longitud.toFixed(4)}` : '—';
        const locUrl = a.gps_latitud ? `https://maps.google.com/?q=${a.gps_latitud},${a.gps_longitud}` : 'Sin GPS';
        const vecNombre = (a.nombre_vecino || '').replace(/'/g,"\\'").replace(/"/g,"&quot;");

        return `<tr class="${rowCls}">
            <td>${i+1}</td>
            <td><span class="badge badge-${a.estatus}">${a.estatus.replace('_',' ')}</span></td>
            <td><strong>${a.nombre_vecino}</strong></td>
            <td>${a.telefono_vecino}</td>
            <td>${a.num_identificacion}</td>
            <td>${a.direccion_vecino||a.direccion_aproximada||'—'}</td>
            <td style="font-family:monospace;font-size:.72rem">${gps}</td>
            <td style="font-size:.72rem">${hora}</td>
            <td>
                <div style="display:flex; gap:.35rem; align-items:center;">
                    <button class="btn-ver" onclick="verDet('${a.id_emergencia}')" title="Detalle completo">👁️ Ver</button>
                    ${a.gps_latitud ? `<button class="btn-ver" style="color:#00d68f; background:rgba(0,214,143,.12); border-color:rgba(0,214,143,.3);" onclick="verMapaRapido(${a.gps_latitud}, ${a.gps_longitud})" title="Ver en mapa">🗺️ Mapa</button>` : ''}
                    <button class="btn-ver" style="color:#ff8c00; background:rgba(255,140,0,.12); border-color:rgba(255,140,0,.3);" onclick="avisarFamiliares('${a.id_vecino}', '${vecNombre}', '${locUrl}')" title="Avisar a familiares">💬 Avisar</button>
                </div>
            </td>
        </tr>`;
    }).join('');
}

// ── DETALLE ───────────────────────────────────────
async function verDet(id) {
    try {
        const res = await fetch(`${API}/api/emergencias/${INST.id_institucion}`);
        const lista = await res.json();
        alertaActual = lista.find(a=>a.id_emergencia===id);
    } catch { return; }
    if (!alertaActual) return;
    const a = alertaActual;
    const mUrl = a.gps_latitud ? `https://maps.google.com/?q=${a.gps_latitud},${a.gps_longitud}` : null;

    document.getElementById('det-body').innerHTML = `
    <div class="det-grid">
        <div class="det-item"><div class="det-label">Vecino</div><div class="det-val">👤 ${a.nombre_vecino}</div></div>
        <div class="det-item"><div class="det-label">Teléfono</div><div class="det-val">📱 ${a.telefono_vecino}</div></div>
        <div class="det-item"><div class="det-label">Identificación</div><div class="det-val">🪪 ${a.num_identificacion}</div></div>
        <div class="det-item"><div class="det-label">Estado</div><div class="det-val"><span class="badge badge-${a.estatus}">${a.estatus.replace('_',' ')}</span></div></div>
        <div class="det-item det-full"><div class="det-label">Dirección</div><div class="det-val">${a.direccion_vecino||'—'} ${a.direccion_aproximada||''}</div></div>
        <div class="det-item det-full">
            <div class="det-label">Coordenadas GPS</div>
            <div class="det-val">📍 ${a.gps_latitud?`${a.gps_latitud.toFixed(6)}, ${a.gps_longitud.toFixed(6)}`:'No disponible'}</div>
            ${mUrl?`<a class="map-link" href="${mUrl}" target="_blank">🗺️ Abrir en Google Maps</a>`:''}
        </div>
        <div class="det-item"><div class="det-label">Fecha / Hora</div><div class="det-val">${new Date(a.fecha_creacion + 'Z').toLocaleString([], { timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone })}</div></div>
        ${a.notas_operador?`<div class="det-item"><div class="det-label">Notas</div><div class="det-val">${a.notas_operador}</div></div>`:''}
    </div>`;

    document.getElementById('modal-det').style.display='flex';
    if (mapaL && a.gps_latitud) { mapaL.setView([a.gps_latitud,a.gps_longitud],16); if(marcadores[id]) marcadores[id].openPopup(); }
}
function closeDet(e) {
    if (e && e.target!==document.getElementById('modal-det')) return;
    document.getElementById('modal-det').style.display='none'; alertaActual=null;
}
async function cambiarEstatus(estatus) {
    if (!alertaActual) return;
    try {
        await fetch(`${API}/api/emergencias/${alertaActual.id_emergencia}/estatus`,{
            method:'PATCH', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({estatus})
        });
        closeDet(); await cargarAlertas();
    } catch { alert('Error al actualizar.'); }
}

// ── VECINOS ───────────────────────────────────────
async function cargarVecinos() {
    try {
        const res = await fetch(`${API}/api/vecinos/${INST.id_institucion}`);
        const vec = await res.json();
        document.getElementById('sp-vec').textContent = vec.length;
        const tbody = document.getElementById('vecinos-tbody');
        if (!vec.length) { tbody.innerHTML=`<tr><td colspan="6"><div class="empty-state"><p>Sin vecinos registrados</p></div></td></tr>`; return; }
        tbody.innerHTML = vec.map((v,i)=>`
            <tr>
                <td>${i+1}</td>
                <td><strong>${v.nombre}</strong></td>
                <td>${v.telefono}</td>
                <td>${v.num_identificacion}</td>
                <td>${v.direccion||'—'}</td>
                <td style="font-size:.72rem">${new Date(v.fecha_registro + 'Z').toLocaleDateString([], { timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone })}</td>
            </tr>`).join('');
    } catch { document.getElementById('vecinos-tbody').innerHTML=`<tr><td colspan="6"><div class="empty-state"><p>Sin conexión</p></div></td></tr>`; }
}

// ── CLAVES ────────────────────────────────────────
function abrirClaves() {
    const base = window.location.origin + window.location.pathname.replace('panel.html','');
    const link = `${base}vecino.html?inst=${INST.id_institucion}`;
    document.getElementById('link-vecino-val').textContent = link;
    document.getElementById('clave-box').style.display='none';
    document.getElementById('modal-claves').style.display='flex';
    cargarClaves();
}
function closeClaves(e) {
    if (e && e.target!==document.getElementById('modal-claves')) return;
    document.getElementById('modal-claves').style.display='none';
}
function copiarLink() {
    const v = document.getElementById('link-vecino-val').textContent;
    navigator.clipboard.writeText(v).catch(()=>prompt('Copie:',v));
}

async function generarClave() {
    const desc = document.getElementById('clave-desc').value.trim();
    try {
        const res = await fetch(`${API}/api/vecinos/claves`,{
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify({id_institucion:INST.id_institucion, descripcion:desc})
        });
        const c = await res.json();
        document.getElementById('clave-val').textContent = c.clave;
        document.getElementById('clave-box').style.display='block';
        document.getElementById('clave-desc').value='';
        await cargarClaves();
    } catch { alert('Error al generar clave.'); }
}
function copiarClave() {
    const v = document.getElementById('clave-val').textContent;
    navigator.clipboard.writeText(v).catch(()=>prompt('Copie:',v));
}

async function cargarClaves() {
    try {
        const res = await fetch(`${API}/api/vecinos/claves/${INST.id_institucion}`);
        const claves = await res.json();
        const el = document.getElementById('claves-list');
        if (!claves.length) { el.innerHTML='<p style="color:#6b7294;font-size:.82rem;">No hay claves generadas aún.</p>'; return; }
        el.innerHTML = claves.map(c=>`
            <div class="clave-item">
                <span class="clave-code">${c.clave}</span>
                <span class="clave-desc">${c.descripcion||'Sin descripción'}</span>
                <span class="${c.usada?'badge-usada':'badge-libre'}">${c.usada?'Usada':'Libre'}</span>
                <button class="btn-del" onclick="eliminarClave(${c.id_clave})">🗑</button>
            </div>`).join('');
    } catch { document.getElementById('claves-list').innerHTML='<p style="color:#6b7294;font-size:.82rem;">Sin conexión.</p>'; }
}
async function eliminarClave(id) {
    if (!confirm('¿Eliminar clave?')) return;
    try { await fetch(`${API}/api/vecinos/claves/${id}`,{method:'DELETE'}); await cargarClaves(); }
    catch { alert('Error al eliminar.'); }
}
