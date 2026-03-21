/**
 * Vecino JS — Botón de Pánico SISDEL
 * Soporta: acceso con clave personal ó acceso directo con link (?inst=...)
 */

const API = (window.location.hostname === 'localhost' || window.location.protocol === 'file:') ? 'http://localhost:8000' : 'https://boton-de-panico-sisdel.onrender.com';  // Local o Render
let vecinoData   = null;   // datos del vecino
let instData     = null;   // datos de la institución (del URL o de la clave)
let gpsLat       = null;
let gpsLon       = null;
let holdInterval = null;
let holdProgress = 0;

// ── LADA / PAÍS ────────────────────────────────
function actualizarLada() {
    const codigo = document.getElementById('reg-pais')?.value || '502';
    const badge  = document.getElementById('lada-badge');
    if (badge) badge.textContent = '+' + codigo;
    document.querySelectorAll('.lada-fam').forEach(el => el.textContent = '+' + codigo);
}

function leerContactosFamiliares() {
    const codigo = document.getElementById('reg-pais')?.value || '502';
    const contactos = [];
    for (let i = 1; i <= 5; i++) {
        const nombre = document.getElementById(`fam-nombre-${i}`)?.value.trim() || '';
        const tel    = (document.getElementById(`fam-tel-${i}`)?.value || '').replace(/\D/g,'');
        if (tel) contactos.push({ nombre, telefono: codigo + tel });
    }
    return contactos;
}

function cargarContactosFamiliaresEnForm(contactos) {
    if (!contactos) return;
    for (let i = 0; i < 5; i++) {
        const c = contactos[i] || {};
        const nombreEl = document.getElementById(`fam-nombre-${i+1}`);
        const telEl    = document.getElementById(`fam-tel-${i+1}`);
        if (nombreEl) nombreEl.value = c.nombre || '';
        // Quitar lada del tel al mostrarlo en el campo
        if (telEl && c.telefono) {
            const codigo = document.getElementById('reg-pais')?.value || '502';
            telEl.value = c.telefono.replace(new RegExp('^' + codigo), '');
        }
    }
}
let modoVecinoLogin = false;  // true cuando vecino accede con su código
const HOLD_MS    = 3000;

// ── INIT ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    // Leer ?inst= del URL
    const params    = new URLSearchParams(window.location.search);
    const instId    = params.get('inst');
    const modoLink  = !!instId; // true = accedió por link
    const modoAdmin = params.get('admin') === '1'; // true = abierto desde panel admin

    // Intentar cargar datos de la institución para mostrar su nombre
    if (instId) {
        try {
            const res  = await fetch(`${API}/api/programador/instituciones`);
            const list = await res.json();
            instData   = list.find(i => i.id_institucion === instId) || null;
            if (instData) {
                document.getElementById('inst-nombre-label').textContent = instData.nombre_institucion;
            }
        } catch { /* sin servidor, continuar */ }
    }

    // Si es modo admin → ir directo al formulario de registro (nuevo vecino)
    if (modoAdmin && instId) {
        mostrarPaso('paso-registro');
        // Mostrar botón Ver Vecinos y botón X
        const btnVV = document.getElementById('btn-ver-vecinos');
        if (btnVV) btnVV.style.display = 'inline-flex';
        const btnX = document.getElementById('btn-cerrar-form');
        if (btnX) btnX.style.display = 'flex';
        return;
    }

    // Si es modo vecino → cargar datos e ir al botón de pánico
    const modoVecino = params.get('vecino') === '1';
    const numIdParam = params.get('numid');
    if (modoVecino && instId && numIdParam) {
        modoVecinoLogin = true;
        try {
            const res = await fetch(`${API}/api/vecinos/buscar/${instId}/${encodeURIComponent(numIdParam)}`);
            if (res.ok) {
                const v = await res.json();
                vecinoData = v;
                instData   = instData || { id_institucion: instId };
                sessionStorage.setItem('sisdel_vecino', JSON.stringify(vecinoData));
                mostrarPaso('paso-panico');
                iniciarPasoParanica();
            } else {
                mostrarPaso('paso-registro');
            }
        } catch {
            mostrarPaso('paso-registro');
        }
        return;
    }

    // Enter en clave
    document.getElementById('inp-clave').addEventListener('keydown', e => {
        if (e.key === 'Enter') validarClave();
    });

    // ¿Hay sesión previa guardada?
    const savedVecino = sessionStorage.getItem('sisdel_vecino');
    const savedInst   = sessionStorage.getItem('sisdel_vecino_inst');

    if (savedVecino) {
        vecinoData = JSON.parse(savedVecino);
        if (savedInst) instData = JSON.parse(savedInst);
        mostrarPaso('paso-panico');
        iniciarPasoParanica();
        return;
    }

    // Si vino con link Y hay datos en localStorage → pre-cargar
    if (modoLink) {
        const localData = localStorage.getItem(`sisdel_vecino_${instId}`);
        if (localData) {
            vecinoData = JSON.parse(localData);
            sessionStorage.setItem('sisdel_vecino', JSON.stringify(vecinoData));
            mostrarPaso('paso-panico');
            iniciarPasoParanica();
        }
        // Si no hay datos locales → mostrar clave input con opción de saltar
    }
});

// ── PASOS ─────────────────────────────────────────
function mostrarPaso(id) {
    ['paso-clave','paso-registro','paso-panico'].forEach(p => {
        document.getElementById(p).style.display = p === id ? 'flex' : 'none';
    });
}
function mostrarError(elId, msg) {
    const el = document.getElementById(elId);
    el.textContent = msg; el.style.display = 'block';
    setTimeout(() => el.style.display='none', 4000);
}

// ── PASO 1A: CON CLAVE ────────────────────────────
async function validarClave() {
    const clave = document.getElementById('inp-clave').value.trim().toUpperCase();
    if (clave.length !== 6) { mostrarError('error-clave','La clave debe tener 6 caracteres'); return; }

    const btn = document.getElementById('btn-validar');
    btn.disabled = true; btn.textContent = 'Verificando...';

    const params = new URLSearchParams(window.location.search);
    const instId = params.get('inst') || null;

    try {
        const res  = await fetch(`${API}/api/vecinos/claves/validar`, {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ clave, id_institucion: instId })
        });
        const data = await res.json();

        if (data.valida) {
            sessionStorage.setItem('sisdel_clave_vecino', clave);
            // Guardar inst para scope de emergencias
            if (data.vecino) {
                // Ya registrado → ir directo a pánico
                vecinoData = data.vecino;
                sessionStorage.setItem('sisdel_vecino', JSON.stringify(vecinoData));
                mostrarPaso('paso-panico');
                iniciarPasoParanica();
            } else {
                // Primera vez → formulario
                mostrarPaso('paso-registro');
            }
        } else {
            mostrarError('error-clave','Clave inválida. Solicítela al coordinador de su colonia.');
        }
    } catch {
        mostrarError('error-clave','Sin conexión. Intente con el link directo o más tarde.');
    } finally {
        btn.disabled = false; btn.textContent = 'Continuar →';
    }
}

// ── PASO 1B: ACCESO SOLO CON LINK ─────────────────
function accederSinClave() {
    const params = new URLSearchParams(window.location.search);
    const instId = params.get('inst');
    if (!instId) {
        mostrarError('error-clave','Este link no contiene un código de institución válido.');
        return;
    }
    mostrarPaso('paso-registro');
}

// ── PASO 2: REGISTRO ──────────────────────────────

// Auto-relleno al salir del campo de identificación
async function buscarVecinoPorId() {
    const numId = document.getElementById('reg-id').value.trim();
    const hintEl = document.getElementById('hint-id');
    if (!numId || numId.length < 2) { hintEl.style.display='none'; return; }

    const params = new URLSearchParams(window.location.search);
    const instId = params.get('inst') || (instData && instData.id_institucion) || '';
    if (!instId) return;

    try {
        const res = await fetch(`${API}/api/vecinos/buscar/${instId}/${encodeURIComponent(numId)}`);
        if (res.ok) {
            const v = await res.json();
            document.getElementById('reg-nombre').value   = v.nombre || '';
            document.getElementById('reg-telefono').value  = v.telefono || '';
            document.getElementById('reg-dir').value       = v.direccion || '';
            document.getElementById('reg-correo').value    = v.correo || '';
            document.getElementById('reg-sexo').value      = v.sexo || '';
            document.getElementById('reg-edad').value      = v.edad || '';
            hintEl.textContent = '✅ Vecino encontrado — datos auto-rellenados';
            hintEl.className = 'v-hint found';
            hintEl.style.display = 'block';
            // Guardar id_vecino para poder Modificar/Eliminar
            window._vecinoEditId = v.id_vecino;
            // Mostrar botones si es admin
            const modoAdmin = new URLSearchParams(window.location.search).get('admin') === '1';
            if (modoAdmin) {
                document.getElementById('btn-guardar')?.setAttribute('style','flex:2;display:none');
                document.getElementById('btn-modificar')?.style.setProperty('display','inline-flex');
                document.getElementById('btn-eliminar')?.style.setProperty('display','inline-flex');
            }
        } else {
            hintEl.textContent = 'Nuevo vecino — complete todos los campos';
            hintEl.className = 'v-hint notfound';
            hintEl.style.display = 'block';
            window._vecinoEditId = null;
            // Restaurar botón guardar
            document.getElementById('btn-guardar')?.removeAttribute('style');
            document.getElementById('btn-modificar')?.style.setProperty('display','none');
            document.getElementById('btn-eliminar')?.style.setProperty('display','none');
        }
    } catch {
        hintEl.style.display = 'none';
    }
}

async function registrarVecino() {
    const nombre   = document.getElementById('reg-nombre').value.trim();
    const telefono = document.getElementById('reg-telefono').value.trim();
    const numId    = document.getElementById('reg-id').value.trim();
    const dir      = document.getElementById('reg-dir').value.trim();
    const sexo     = document.getElementById('reg-sexo').value;
    const edad     = parseInt(document.getElementById('reg-edad').value) || 0;
    const correo   = document.getElementById('reg-correo').value.trim();
    const waNum    = (document.getElementById('reg-whatsapp')?.value || '').replace(/\D/g,'');

    if (!nombre || !telefono || !numId) {
        mostrarError('error-registro','Nombre, teléfono e identificación son obligatorios');
        return;
    }

    const params = new URLSearchParams(window.location.search);
    const instId = params.get('inst') || (instData && instData.id_institucion) || null;
    const clave  = sessionStorage.getItem('sisdel_clave_vecino') || '';

    const payload = {
        id_institucion: instId || '',
        nombre, telefono, num_identificacion: numId,
        direccion: dir, sexo, edad, correo,
        clave_acceso: clave
    };
    // Guardar WhatsApp localmente (no se envía al backend)
    if (waNum) sessionStorage.setItem('sisdel_wa', waNum);

    try {
        const res = await fetch(`${API}/api/vecinos/registro`, {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            vecinoData = await res.json();
        } else {
            const err = await res.json();
            // Pydantic devuelve detail como array de objetos
            let msg = 'Error al registrar';
            if (typeof err.detail === 'string') {
                msg = err.detail;
            } else if (Array.isArray(err.detail)) {
                msg = err.detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ');
            }
            mostrarError('error-registro', msg);
            return;
        }
    } catch {
        vecinoData = { nombre, telefono, num_identificacion: numId, direccion: dir,
                       sexo, edad, correo, id_institucion: instId, codigo_vecino: '' };
    }

    sessionStorage.setItem('sisdel_vecino', JSON.stringify(vecinoData));
    if (instId) localStorage.setItem(`sisdel_vecino_${instId}`, JSON.stringify(vecinoData));
    if (instData) sessionStorage.setItem('sisdel_vecino_inst', JSON.stringify(instData));
    // Guardar contactos de emergencia en backend + sessionStorage
    const contactosFam = leerContactosFamiliares();
    if (contactosFam.length) {
        sessionStorage.setItem('sisdel_familiares', JSON.stringify(contactosFam));
        // Guardar en PostgreSQL
        if (vecinoData.id_vecino) {
            fetch(`${API}/api/vecinos/${vecinoData.id_vecino}/contactos`, {
                method: 'POST', headers: {'Content-Type':'application/json'},
                body: JSON.stringify(contactosFam)
            }).catch(() => {});
        }
    }

    // Si es vecino actualizando → volver al botón de pánico
    if (modoVecinoLogin) {
        mostrarPaso('paso-panico');
        iniciarPasoParanica();
        return;
    }

    // Mostrar código generado si existe (solo en primer registro)
    const codigo = vecinoData.codigo_vecino || '';
    if (codigo) {
        document.getElementById('codigo-generado-val').textContent = codigo;
        document.getElementById('codigo-generado-box').style.display = 'block';
        // Ocultar botón guardar
        const btnGuardar = document.querySelector('.btn-registrar');
        if (btnGuardar) btnGuardar.style.display = 'none';
    } else {
        mostrarPaso('paso-panico');
        iniciarPasoParanica();
    }
}

function continuarDespuesRegistro() {
    mostrarPaso('paso-panico');
    iniciarPasoParanica();
}

// ── PASO 3: PÁNICO ────────────────────────────────
function iniciarPasoParanica() {
    if (!vecinoData) return;
    document.getElementById('vecino-nombre-bar').textContent = vecinoData.nombre || 'Vecino';
    // Cargar WhatsApp de emergencia guardado
    vecinoData.whatsapp_emergencia = sessionStorage.getItem('sisdel_wa') || vecinoData.whatsapp_emergencia || '';
    // Cargar contactos de emergencia desde backend
    if (vecinoData.id_vecino && !sessionStorage.getItem('sisdel_familiares')) {
        fetch(`${API}/api/vecinos/${vecinoData.id_vecino}/contactos`)
            .then(r => r.ok ? r.json() : [])
            .then(contactos => {
                if (contactos.length) {
                    sessionStorage.setItem('sisdel_familiares', JSON.stringify(contactos));
                }
            }).catch(() => {});
    }
    obtenerGPS();
}

function obtenerGPS() {
    const statusEl = document.getElementById('gps-status');
    const dot      = document.getElementById('gps-dot');

    if (!navigator.geolocation) {
        usarGeolocalizacionIP(statusEl, dot);
        return;
    }

    statusEl.textContent = '📡 Solicitando ubicación...';

    // FASE 1: posición rápida (acepta caché de hasta 30 seg, baja precisión)
    navigator.geolocation.getCurrentPosition(
        pos => {
            gpsLat = pos.coords.latitude;
            gpsLon = pos.coords.longitude;
            statusEl.textContent = `📍 ${gpsLat.toFixed(5)}, ${gpsLon.toFixed(5)} (ajustando...)`;
            dot.style.background = '#ff8c00';
        },
        () => {}, // silencioso si falla fase 1
        { enableHighAccuracy: false, timeout: 5000, maximumAge: 30000 }
    );

    // FASE 2: seguimiento continuo de alta precisión
    navigator.geolocation.watchPosition(
        pos => {
            gpsLat = pos.coords.latitude;
            gpsLon = pos.coords.longitude;
            const acc = pos.coords.accuracy ? ` (±${Math.round(pos.coords.accuracy)}m)` : '';
            statusEl.textContent = `📍 ${gpsLat.toFixed(5)}, ${gpsLon.toFixed(5)}${acc}`;
            dot.style.background = '#00d68f';
        },
        err => {
            if (err.code === 1) {
                // Permiso denegado → usar IP como respaldo automático
                usarGeolocalizacionIP(statusEl, dot);
            } else if (!gpsLat) {
                statusEl.textContent = '🟡 Sin señal GPS — la alerta se enviará sin coordenadas';
                dot.style.background = '#ff8c00';
            }
        },
        { enableHighAccuracy: true, maximumAge: 10000 }
    );
}

async function usarGeolocalizacionIP(statusEl, dot) {
    // Respaldo automático: geolocalización por IP (no requiere permiso)
    statusEl.textContent = '🌐 Obteniendo ubicación por red...';
    dot.style.background = '#ff8c00';
    try {
        const res  = await fetch('https://ipapi.co/json/');
        const data = await res.json();
        if (data.latitude && data.longitude) {
            gpsLat = parseFloat(data.latitude);
            gpsLon = parseFloat(data.longitude);
            const ciudad = data.city || data.region || 'Ciudad';
            statusEl.textContent = `🌐 ${ciudad} (${gpsLat.toFixed(3)}, ${gpsLon.toFixed(3)}) — aprox. por red`;
            dot.style.background = '#ff8c00';
        } else {
            statusEl.textContent = '⚠️ Sin ubicación — alerta se enviará sin coordenadas';
        }
    } catch {
        statusEl.textContent = '⚠️ Sin ubicación — alerta se enviará sin coordenadas';
    }
}

function editarDatos() {
    if (vecinoData) {
        document.getElementById('reg-nombre').value   = vecinoData.nombre || '';
        document.getElementById('reg-telefono').value = vecinoData.telefono || '';
        document.getElementById('reg-id').value       = vecinoData.num_identificacion || '';
        document.getElementById('reg-dir').value      = vecinoData.direccion || '';
        document.getElementById('reg-correo').value   = vecinoData.correo || '';
        document.getElementById('reg-sexo').value     = vecinoData.sexo || '';
        document.getElementById('reg-edad').value     = vecinoData.edad || '';
    }

    // Si vino del login como vecino → bloquear campos de identidad
    if (modoVecinoLogin) {
        ['reg-id','reg-nombre','reg-correo','reg-edad'].forEach(id => {
            const el = document.getElementById(id);
            if (el) { el.readOnly = true; el.style.opacity = '0.5'; }
        });
        const sexoEl = document.getElementById('reg-sexo');
        if (sexoEl) { sexoEl.disabled = true; sexoEl.style.opacity = '0.5'; }
        document.getElementById('hint-id').style.display = 'none';
        const btn = document.querySelector('.btn-registrar');
        if (btn) btn.textContent = '💾 Actualizar Datos';
    }

    // Reset UI
    document.getElementById('codigo-generado-box').style.display = 'none';
    const btnGuardar = document.querySelector('.btn-registrar');
    if (btnGuardar) btnGuardar.style.display = 'block';
    mostrarPaso('paso-registro');
}

// ── HOLD TO PANIC ─────────────────────────────────
function iniciarPanico(e) {
    e.preventDefault();
    document.getElementById('btn-panico').classList.add('pressing');
    document.getElementById('hold-bar-wrap').style.display = 'block';
    document.getElementById('hint-panico').textContent = '¡Mantén presionado!';
    holdProgress = 0;
    const start = Date.now();
    holdInterval = setInterval(() => {
        holdProgress = Math.min(((Date.now()-start)/HOLD_MS)*100, 100);
        document.getElementById('hold-bar').style.width = holdProgress+'%';
        if (holdProgress >= 100) { clearInterval(holdInterval); holdInterval=null; enviarAlerta(); }
    }, 50);
}
function cancelarPanico(e) {
    e.preventDefault();
    document.getElementById('btn-panico').classList.remove('pressing');
    if (holdInterval) { clearInterval(holdInterval); holdInterval=null; }
    if (holdProgress < 100) {
        document.getElementById('hold-bar-wrap').style.display='none';
        document.getElementById('hold-bar').style.width='0%';
        document.getElementById('hint-panico').textContent='Mantén presionado 3 segundos para enviar alerta';
    }
}

let _alertaCount = 0;          // cuántas alertas se han enviado
let _countdownInterval = null; // temporizador auto-cierre

async function enviarAlerta() {
    if (!vecinoData) return;
    if (_alertaCount >= 10) {
        alert('Has enviado 10 alertas. El panel ya fue notificado. Mantén la calma.');
        return;
    }

    _alertaCount++;
    const instId = vecinoData.id_institucion || new URLSearchParams(window.location.search).get('inst') || '';

    const payload = {
        id_institucion:    instId,
        id_vecino:         vecinoData.id_vecino    || null,
        nombre_vecino:     vecinoData.nombre        || 'Sin nombre',
        telefono_vecino:   vecinoData.telefono      || 'Sin teléfono',
        num_identificacion:vecinoData.num_identificacion || 'Sin ID',
        direccion_vecino:  vecinoData.direccion     || '',
        gps_latitud:       gpsLat,
        gps_longitud:      gpsLon,
        direccion_aproximada: gpsLat ? `${gpsLat.toFixed(6)}, ${gpsLon.toFixed(6)}` : 'Sin coordenadas'
    };

    if (navigator.vibrate) navigator.vibrate([200,100,200,100,500]);

    // Mostrar overlay con contador
    document.getElementById('env-alerta-num').textContent = `Alerta #${_alertaCount} de 10`;
    document.getElementById('env-coords').textContent =
        gpsLat ? `📍 ${gpsLat.toFixed(6)}, ${gpsLon.toFixed(6)}` : '📍 Sin coordenadas GPS';
    // Mostrar/ocultar botón "enviar otra"
    const btnOtra = document.getElementById('btn-otra-alerta');
    if (btnOtra) btnOtra.style.display = _alertaCount < 10 ? 'inline-block' : 'none';

    document.getElementById('overlay-enviado').style.display='flex';

    // Auto-cierre en 5 segundos
    let secs = 5;
    const cdEl = document.getElementById('env-countdown');
    if (_countdownInterval) clearInterval(_countdownInterval);
    if (cdEl) {
        cdEl.textContent = `Cerrando en ${secs}s...`;
        _countdownInterval = setInterval(() => {
            secs--;
            if (secs <= 0) { clearInterval(_countdownInterval); ocultarConfirmacion(); }
            else if (cdEl) cdEl.textContent = `Cerrando en ${secs}s...`;
        }, 1000);
    }

    // Reset botón
    document.getElementById('btn-panico').classList.remove('pressing');
    document.getElementById('hold-bar-wrap').style.display='none';
    document.getElementById('hold-bar').style.width='0%';
    document.getElementById('hint-panico').textContent='Mantén presionado 3 segundos para enviar alerta';

    // Enviar al backend
    try {
        await fetch(`${API}/api/emergencias/`, {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify(payload)
        });
    } catch {
        const pendientes = JSON.parse(localStorage.getItem('sisdel_pendientes')||'[]');
        pendientes.push({...payload, ts: new Date().toISOString()});
        localStorage.setItem('sisdel_pendientes', JSON.stringify(pendientes));
    }

    // WhatsApp: mostrar botones directos en el overlay (evita bloqueador de pop-ups)
    const loc        = gpsLat ? `https://maps.google.com/?q=${gpsLat},${gpsLon}` : 'Sin GPS';
    const textoWA    = `🚨 EMERGENCIA 🚨\n${vecinoData.nombre} ha activado el botón de pánico.\n📍 Ubicación: ${loc}\n📱 Tel: ${vecinoData.telefono}`;
    const familiares = JSON.parse(sessionStorage.getItem('sisdel_familiares') || '[]');
    const waNumber   = vecinoData.whatsapp_emergencia;

    // Construir lista de contactos a notificar
    const contactosWA = [...familiares];
    if (waNumber && !familiares.length) contactosWA.push({ nombre: 'Familiar', telefono: waNumber });

    const waBotones = document.getElementById('wa-botones');
    const waSection = document.getElementById('wa-familiares');
    if (waBotones && contactosWA.length > 0) {
        waBotones.innerHTML = contactosWA.map(fam => {
            const url = `https://wa.me/${fam.telefono}?text=${encodeURIComponent(textoWA)}`;
            return `<a href="${url}" target="_blank" rel="noopener"
                style="display:block;background:#25d366;color:#fff;text-align:center;padding:.5rem 1rem;
                       border-radius:10px;font-weight:700;font-size:.88rem;text-decoration:none;">
                💬 Avisar a ${fam.nombre || fam.telefono}
            </a>`;
        }).join('');
        if (waSection) waSection.style.display = 'block';
    } else if (waSection) {
        waSection.style.display = 'none';
    }
}

function enviarOtraAlerta() {
    if (_countdownInterval) clearInterval(_countdownInterval);
    ocultarConfirmacion();
    // Pequeña pausa antes de enviar (UX)
    setTimeout(() => enviarAlerta(), 300);
}

function ocultarConfirmacion() {
    if (_countdownInterval) { clearInterval(_countdownInterval); _countdownInterval = null; }
    const cdEl = document.getElementById('env-countdown');
    if (cdEl) cdEl.textContent = '';
    document.getElementById('overlay-enviado').style.display='none';
}

// ── LISTA DE VECINOS (solo admin) ─────────────────────────

let _todosVecinos = [];

async function abrirListaVecinos() {
    const params = new URLSearchParams(window.location.search);
    const instId = params.get('inst');
    if (!instId) return;

    // Nombre instón en cabecera
    const nombreEl = document.getElementById('modal-inst-nombre');
    if (instData) nombreEl.textContent = instData.nombre_institucion || '';

    // Limpiar
    document.getElementById('buscar-vecino-lista').value = '';
    document.getElementById('vecinos-tbody').innerHTML = '<tr><td colspan="8" style="text-align:center;padding:1.5rem;color:#6b7294;">Cargando...</td></tr>';
    document.getElementById('modal-vecinos').style.display = 'block';
    document.body.style.overflow = 'hidden';

    try {
        const res = await fetch(`${API}/api/vecinos/${instId}`);
        _todosVecinos = await res.json();
        renderTablaVecinos(_todosVecinos);
    } catch {
        document.getElementById('vecinos-tbody').innerHTML = '<tr><td colspan="8" style="text-align:center;color:#ff3b3b;padding:1rem;">Error al cargar vecinos</td></tr>';
    }
}

function renderTablaVecinos(lista) {
    const tbody = document.getElementById('vecinos-tbody');
    const vacio = document.getElementById('vecinos-vacio');
    if (!lista.length) {
        tbody.innerHTML = '';
        vacio.style.display = 'block';
        return;
    }
    vacio.style.display = 'none';
    tbody.innerHTML = lista.map((v, i) => `
        <tr style="border-bottom:1px solid #1a1f3e; ${i%2===0 ? 'background:rgba(30,35,70,.4)' : ''}">
            <td style="padding:.55rem .8rem; color:#4da6ff; font-weight:700;">${i+1}</td>
            <td style="padding:.55rem .8rem; font-weight:600;">${v.nombre}</td>
            <td style="padding:.55rem .8rem; font-family:monospace; color:#7c5cfc;">${v.num_identificacion}</td>
            <td style="padding:.55rem .8rem;">${v.telefono}</td>
            <td style="padding:.55rem .8rem; text-align:center;">${v.sexo || '—'}</td>
            <td style="padding:.55rem .8rem; text-align:center;">${v.edad || '—'}</td>
            <td style="padding:.55rem .8rem; color:#6b7294;">${v.direccion || '—'}</td>
            <td style="padding:.55rem .8rem; font-family:monospace; font-weight:800; color:#00d68f; letter-spacing:3px;">${v.codigo_vecino || '—'}</td>
        </tr>
    `).join('');
}

function filtrarVecinos() {
    const q = document.getElementById('buscar-vecino-lista').value.toLowerCase().trim();
    if (!q) { renderTablaVecinos(_todosVecinos); return; }
    const filtrados = _todosVecinos.filter(v =>
        (v.nombre||'').toLowerCase().includes(q) ||
        (v.num_identificacion||'').toLowerCase().includes(q) ||
        (v.telefono||'').toLowerCase().includes(q) ||
        (v.codigo_vecino||'').toLowerCase().includes(q)
    );
    renderTablaVecinos(filtrados);
}

function cerrarListaVecinos() {
    document.getElementById('modal-vecinos').style.display = 'none';
    document.body.style.overflow = '';
}

// ── BOTÓN X / CERRAR FORMULARIO ─────────────────────────
function cerrarFormulario() {
    if (vecinoData) {
        // Vecino vuelve al botón de pánico
        mostrarPaso('paso-panico');
        iniciarPasoParanica();
    } else {
        // Admin: cerrar pestaña o ir atrás
        if (window.history.length > 1) window.history.back();
        else window.close();
    }
}

// ── MODIFICAR VECINO (admin) ─────────────────────────────
async function modificarVecino() {
    const id = window._vecinoEditId;
    if (!id) { alert('Busca primero al vecino por su documento.'); return; }

    const lada   = document.getElementById('reg-pais')?.value || '502';
    const telRaw = document.getElementById('reg-telefono').value.replace(/\D/g,'');
    const data   = {
        nombre:    document.getElementById('reg-nombre').value.trim(),
        telefono:  lada + telRaw,
        direccion: document.getElementById('reg-dir').value.trim(),
        sexo:      document.getElementById('reg-sexo').value,
        edad:      parseInt(document.getElementById('reg-edad').value) || 0,
        correo:    document.getElementById('reg-correo').value.trim()
    };

    try {
        const res = await fetch(`${API}/api/vecinos/${id}`, {
            method: 'PUT', headers: {'Content-Type':'application/json'},
            body: JSON.stringify(data)
        });
        if (res.ok) {
            const hintEl = document.getElementById('hint-id');
            hintEl.textContent = '✅ Datos actualizados correctamente';
            hintEl.style.color = '#00d68f';
            hintEl.style.display = 'block';
            setTimeout(() => hintEl.style.display = 'none', 3000);
        } else {
            alert('Error al modificar el vecino.');
        }
    } catch {
        alert('Sin conexión al servidor.');
    }
}

// ── ELIMINAR VECINO (admin) ──────────────────────────────
async function eliminarVecino() {
    const id     = window._vecinoEditId;
    const nombre = document.getElementById('reg-nombre').value || 'este vecino';
    if (!id) { alert('Busca primero al vecino por su documento.'); return; }
    if (!confirm(`⚠️ ¿Eliminar permanentemente a ${nombre}?\n\nEsta acción no se puede deshacer.`)) return;

    try {
        const res = await fetch(`${API}/api/vecinos/${id}`, { method: 'DELETE' });
        if (res.ok) {
            alert(`✅ ${nombre} eliminado correctamente.`);
            // Limpiar formulario
            ['reg-id','reg-nombre','reg-telefono','reg-dir','reg-correo','reg-edad'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.value = '';
            });
            document.getElementById('reg-sexo').value = '';
            window._vecinoEditId = null;
            document.getElementById('btn-guardar')?.removeAttribute('style');
            document.getElementById('btn-modificar')?.style.setProperty('display','none');
            document.getElementById('btn-eliminar')?.style.setProperty('display','none');
            document.getElementById('hint-id').style.display = 'none';
        } else {
            alert('Error al eliminar. Intente de nuevo.');
        }
    } catch {
        alert('Sin conexión al servidor.');
    }
}
