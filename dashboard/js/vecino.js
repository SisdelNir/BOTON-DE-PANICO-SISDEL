/**
 * Vecino JS — Botón de Pánico SISDEL
 * Soporta: acceso con clave personal ó acceso directo con link (?inst=...)
 */

const API = window.location.protocol === 'file:' ? 'http://localhost:8000' : '';  // Detecta si es local o nube
let vecinoData   = null;   // datos del vecino
let instData     = null;   // datos de la institución (del URL o de la clave)
let gpsLat       = null;
let gpsLon       = null;
let holdInterval = null;
let holdProgress = 0;
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
        return;
    }

    // Si es modo vecino → cargar datos y bloquear campos
    const modoVecino = params.get('vecino') === '1';
    const numIdParam = params.get('numid');
    if (modoVecino && instId && numIdParam) {
        mostrarPaso('paso-registro');
        try {
            const res = await fetch(`${API}/api/vecinos/buscar/${instId}/${encodeURIComponent(numIdParam)}`);
            if (res.ok) {
                const v = await res.json();
                document.getElementById('reg-id').value       = v.num_identificacion || '';
                document.getElementById('reg-nombre').value   = v.nombre || '';
                document.getElementById('reg-telefono').value = v.telefono || '';
                document.getElementById('reg-dir').value      = v.direccion || '';
                document.getElementById('reg-correo').value   = v.correo || '';
                document.getElementById('reg-sexo').value     = v.sexo || '';
                document.getElementById('reg-edad').value     = v.edad || '';
                // Bloquear campos que no se pueden modificar
                document.getElementById('reg-id').readOnly = true;
                document.getElementById('reg-id').style.opacity = '0.5';
                document.getElementById('reg-nombre').readOnly = true;
                document.getElementById('reg-nombre').style.opacity = '0.5';
                document.getElementById('reg-correo').readOnly = true;
                document.getElementById('reg-correo').style.opacity = '0.5';
                document.getElementById('reg-sexo').disabled = true;
                document.getElementById('reg-sexo').style.opacity = '0.5';
                document.getElementById('reg-edad').readOnly = true;
                document.getElementById('reg-edad').style.opacity = '0.5';
                // Cambiar texto del botón
                const btn = document.querySelector('.btn-registrar');
                if (btn) btn.textContent = '💾 Actualizar Datos';
                // Ocultar hint
                document.getElementById('hint-id').style.display = 'none';
            }
        } catch { /* sin servidor */ }
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
        } else {
            hintEl.textContent = 'Nuevo vecino — complete todos los campos';
            hintEl.className = 'v-hint notfound';
            hintEl.style.display = 'block';
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

    // Mostrar código generado si existe
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
    obtenerGPS();
}

function obtenerGPS() {
    const statusEl = document.getElementById('gps-status');
    const dot = document.getElementById('gps-dot');
    if (!navigator.geolocation) { statusEl.textContent='GPS no disponible'; return; }
    statusEl.textContent = 'Obteniendo ubicación...';
    navigator.geolocation.getCurrentPosition(
        pos => {
            gpsLat = pos.coords.latitude; gpsLon = pos.coords.longitude;
            statusEl.textContent = `📍 ${gpsLat.toFixed(5)}, ${gpsLon.toFixed(5)}`;
            dot.classList.add('ok');
        },
        () => { statusEl.textContent='GPS no disponible — alerta sin coordenadas'; dot.style.background='#ff8c00'; },
        { enableHighAccuracy:true, timeout:10000 }
    );
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

async function enviarAlerta() {
    if (!vecinoData) return;

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

    // Mostrar confirmación inmediata
    document.getElementById('env-coords').textContent =
        gpsLat ? `📍 ${gpsLat.toFixed(6)}, ${gpsLon.toFixed(6)}` : '📍 Sin coordenadas GPS';
    document.getElementById('overlay-enviado').style.display='flex';

    // Reset botón
    document.getElementById('btn-panico').classList.remove('pressing');
    document.getElementById('hold-bar-wrap').style.display='none';
    document.getElementById('hold-bar').style.width='0%';
    document.getElementById('hint-panico').textContent='Mantén presionado 3 segundos para enviar alerta';

    try {
        await fetch(`${API}/api/emergencias/`, {
            method:'POST', headers:{'Content-Type':'application/json'},
            body: JSON.stringify(payload)
        });
    } catch {
        // Guardar pendiente si no hay conexión
        const pendientes = JSON.parse(localStorage.getItem('sisdel_pendientes')||'[]');
        pendientes.push({...payload, ts: new Date().toISOString()});
        localStorage.setItem('sisdel_pendientes', JSON.stringify(pendientes));
    }
}

function ocultarConfirmacion() {
    document.getElementById('overlay-enviado').style.display='none';
}
