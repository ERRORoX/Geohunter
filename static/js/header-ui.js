/**
 * Шапка: активная вкладка в навигации по URL.
 */
(function () {
  function normalizePath(p) {
    let s = String(p || "/");
    if (!s.startsWith("/")) s = "/" + s;
    return s.endsWith("/") ? s : s + "/";
  }

  function initActiveTab() {
    const nav = document.getElementById("nav-tools");
    if (!nav) return;

    const cur = normalizePath(location.pathname || "/");
    const links = Array.from(nav.querySelectorAll("a.tool-link"));
    if (!links.length) return;

    let best = null;
    let bestLen = -1;
    for (const a of links) {
      const href = a.getAttribute("href") || "";
      if (!href.startsWith("/")) continue;
      const hp = normalizePath(href);
      if (cur === hp || cur.startsWith(hp)) {
        if (hp.length > bestLen) {
          best = a;
          bestLen = hp.length;
        }
      }
    }

    links.forEach((a) => a.classList.remove("active"));
    if (best) best.classList.add("active");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initActiveTab);
  } else {
    initActiveTab();
  }
})();
