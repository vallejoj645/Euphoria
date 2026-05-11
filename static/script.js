// Toggle mobile menu
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');
    
    if (navToggle) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }
    
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// Format time helper
function formatTime(date) {
    return date.toLocaleTimeString('es-ES', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
}

// Confirm actions
function confirmAction(message) {
    return confirm(message);
}

// ---- Notificaciones sonoras para meseros ----
function playBeep() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const o = ctx.createOscillator();
        const g = ctx.createGain();
        o.type = 'sine';
        o.frequency.value = 1000;
        g.gain.value = 0.1;
        o.connect(g);
        g.connect(ctx.destination);
        o.start();
        setTimeout(() => {
            o.stop();
            ctx.close();
        }, 350);
    } catch (e) {
        // Fallback: nothing
        console.warn('Audio not supported', e);
    }
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'notification-toast';
    toast.textContent = message;
    Object.assign(toast.style, {
        position: 'fixed',
        right: '20px',
        bottom: '20px',
        background: '#333',
        color: '#fff',
        padding: '12px 16px',
        borderRadius: '6px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
        zIndex: 9999,
        opacity: 0,
        transition: 'opacity 200ms'
    });

    document.body.appendChild(toast);
    requestAnimationFrame(() => { toast.style.opacity = 1; });
    setTimeout(() => {
        toast.style.opacity = 0;
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Polling simple para meseros: consultar /notificaciones/pendientes cada 5s
(function startNotificationPolling(){
    if (typeof window.currentUserRole === 'undefined' || window.currentUserRole !== 'mesero') return;

    let lastCheck = new Date().toISOString();

    async function check() {
        try {
            const res = await fetch(`/notificaciones/pendientes?since=${encodeURIComponent(lastCheck)}`);
            if (!res.ok) return;
            const data = await res.json();
            if (Array.isArray(data) && data.length > 0) {
                // Reproducir sonido y mostrar notificación por cada item
                data.forEach(item => {
                    playBeep();
                    showToast(`Pedido listo: Mesa ${item.mesa} — ${item.producto} x${item.cantidad}`);
                    // Actualizar lastCheck al más reciente
                    if (item.estado_actualizado) lastCheck = item.estado_actualizado;
                });
            } else {
                // Actualizar lastCheck para evitar repetir eventos antiguos
                lastCheck = new Date().toISOString();
            }
        } catch (e) {
            console.warn('Error checking notifications', e);
        }
    }

    // Primera comprobación rápida y luego interval
    check();
    setInterval(check, 5000);
})();