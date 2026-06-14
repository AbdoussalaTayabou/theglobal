/* Bandeau cookies — RGPD friendly, minimal, sans dépendance */
(function () {
  var KEY = "gc_cookie_consent_v1";
  var w = window;

  function read() {
    try { return JSON.parse(localStorage.getItem(KEY) || "null"); }
    catch (e) { return null; }
  }
  function write(v) {
    try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) {}
  }
  function emit(state) {
    w.dispatchEvent(new CustomEvent("gc:cookie-consent", { detail: state }));
  }

  function render() {
    if (document.getElementById("gc-cookie-banner")) return;
    var box = document.createElement("div");
    box.id = "gc-cookie-banner";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-label", "Préférences cookies");
    box.innerHTML =
      '<div class="gc-cc-inner">' +
        '<div class="gc-cc-text">' +
          '<strong>🍪 Cookies</strong> — Nous utilisons des cookies strictement nécessaires au ' +
          'fonctionnement du site, et — avec votre accord — des cookies de mesure d\'audience ' +
          'anonymisée. Aucun cookie publicitaire. ' +
          '<a href="/cookies">En savoir plus</a>.' +
        '</div>' +
        '<div class="gc-cc-actions">' +
          '<button type="button" class="gc-cc-btn gc-cc-refuse" data-act="refuse">Refuser</button>' +
          '<button type="button" class="gc-cc-btn gc-cc-accept" data-act="accept">Tout accepter</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(box);

    box.addEventListener("click", function (e) {
      var t = e.target;
      if (!t || !t.dataset || !t.dataset.act) return;
      var accept = t.dataset.act === "accept";
      var state = {
        necessary: true,
        analytics: accept,
        ts: new Date().toISOString()
      };
      write(state);
      box.remove();
      emit(state);
    });
  }

  w.GCCookies = {
    get: read,
    reset: function () {
      try { localStorage.removeItem(KEY); } catch (e) {}
      render();
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      if (!read()) render(); else emit(read());
    });
  } else {
    if (!read()) render(); else emit(read());
  }
})();
