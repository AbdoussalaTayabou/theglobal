/* Notifications push : enregistre le SW puis souscrit à Web Push.
   Utilisation:
     <button data-push-subscribe data-topic="all">Activer les alertes</button>
*/
(function () {
  const SUPPORTED = 'serviceWorker' in navigator && 'PushManager' in window;
  if (!SUPPORTED) return;

  function urlB64ToUint8Array(b64) {
    const pad = '='.repeat((4 - b64.length % 4) % 4);
    const s = (b64 + pad).replace(/-/g, '+').replace(/_/g, '/');
    const raw = atob(s);
    const out = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
    return out;
  }

  async function getPublicKey() {
    const r = await fetch('/push/vapid-public-key');
    if (!r.ok) throw new Error('push disabled');
    return (await r.json()).publicKey;
  }

  async function subscribe(topic) {
    const reg = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
    await navigator.serviceWorker.ready;
    const perm = await Notification.requestPermission();
    if (perm !== 'granted') throw new Error('permission refusée');
    const pub = await getPublicKey();
    let sub = await reg.pushManager.getSubscription();
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlB64ToUint8Array(pub),
      });
    }
    const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
    await fetch('/push/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify({ subscription: sub.toJSON(), topic: topic || 'all' }),
    });
    return true;
  }

  async function unsubscribe() {
    const reg = await navigator.serviceWorker.getRegistration();
    if (!reg) return;
    const sub = await reg.pushManager.getSubscription();
    if (!sub) return;
    const endpoint = sub.endpoint;
    await sub.unsubscribe();
    const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
    await fetch('/push/unsubscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify({ endpoint }),
    });
  }

  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-push-subscribe]');
    if (!btn) return;
    e.preventDefault();
    btn.disabled = true;
    const prev = btn.textContent;
    try {
      await subscribe(btn.dataset.topic || 'all');
      btn.textContent = '🔔 Alertes activées';
    } catch (err) {
      btn.textContent = '⚠ ' + (err.message || 'Erreur');
      btn.disabled = false;
      setTimeout(() => { btn.textContent = prev; }, 3000);
    }
  });

  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-push-unsubscribe]');
    if (!btn) return;
    e.preventDefault();
    await unsubscribe();
    btn.textContent = 'Désactivé';
  });
})();
