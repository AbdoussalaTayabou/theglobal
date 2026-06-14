/* Partage natif : Web Share API + fallback (Twitter/X, Facebook, LinkedIn, copie).
   Usage :
     <div data-share data-url="…" data-title="…" data-text="…"></div>
*/
(function () {
  function render(host) {
    const url = host.dataset.url || location.href;
    const title = host.dataset.title || document.title;
    const text = host.dataset.text || '';
    const enc = encodeURIComponent;
    const canNative = !!navigator.share;

    host.innerHTML = `
      <div class="share-bar" style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
        <span style="font-size:.85rem;color:#555;">Partager :</span>
        ${canNative ? `<button type="button" data-share-native style="padding:6px 12px;border:1px solid #C9A84C;background:#fff;cursor:pointer;border-radius:2px;">↗ Partager</button>` : ''}
        <a href="https://twitter.com/intent/tweet?url=${enc(url)}&text=${enc(title)}" target="_blank" rel="noopener" style="padding:6px 12px;border:1px solid #ddd;background:#fff;color:#0A1628;text-decoration:none;border-radius:2px;font-size:.85rem;">X</a>
        <a href="https://www.facebook.com/sharer/sharer.php?u=${enc(url)}" target="_blank" rel="noopener" style="padding:6px 12px;border:1px solid #ddd;background:#fff;color:#0A1628;text-decoration:none;border-radius:2px;font-size:.85rem;">Facebook</a>
        <a href="https://www.linkedin.com/sharing/share-offsite/?url=${enc(url)}" target="_blank" rel="noopener" style="padding:6px 12px;border:1px solid #ddd;background:#fff;color:#0A1628;text-decoration:none;border-radius:2px;font-size:.85rem;">LinkedIn</a>
        <a href="mailto:?subject=${enc(title)}&body=${enc(text + '\n\n' + url)}" style="padding:6px 12px;border:1px solid #ddd;background:#fff;color:#0A1628;text-decoration:none;border-radius:2px;font-size:.85rem;">Email</a>
        <button type="button" data-share-copy style="padding:6px 12px;border:1px solid #ddd;background:#fff;cursor:pointer;border-radius:2px;font-size:.85rem;">Copier le lien</button>
      </div>`;

    host.querySelector('[data-share-native]')?.addEventListener('click', async () => {
      try { await navigator.share({ title, text, url }); } catch (_) {}
    });
    host.querySelector('[data-share-copy]')?.addEventListener('click', async (e) => {
      try {
        await navigator.clipboard.writeText(url);
        const b = e.currentTarget; const old = b.textContent;
        b.textContent = '✓ Copié'; setTimeout(() => { b.textContent = old; }, 1800);
      } catch (_) {}
    });
  }
  document.querySelectorAll('[data-share]').forEach(render);
})();
