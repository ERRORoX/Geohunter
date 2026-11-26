/**
 * Строка «ОС: …» в шапке: на localhost — реальные данные с сервера (ядро из Python),
 * иначе — ОС/архитектура браузера (User-Agent Client Hints + разбор UA).
 */
(function () {
  function archFromUa(ua) {
    const m = ua.match(/\b(x86_64|amd64|aarch64|arm64|i686|i386|WOW64)\b/i);
    return m ? m[1].replace(/WOW64/i, "x86_64").toLowerCase() : "";
  }

  function fallbackFromUa(ua) {
    const arch = archFromUa(ua);
    const archSuffix = arch ? ` (${arch})` : "";
    if (/Windows NT 10\.0/i.test(ua)) return `ОС: Windows 10/11${archSuffix}`;
    if (/Windows NT 6\.3/i.test(ua)) return `ОС: Windows 8.1${archSuffix}`;
    if (/Windows NT 6\.1/i.test(ua)) return `ОС: Windows 7${archSuffix}`;
    const android = ua.match(/Android\s+([\d.]+)/i);
    if (android) return `ОС: Android ${android[1]}${archSuffix}`;
    if (/iPhone|iPad|iPod/i.test(ua)) {
      const ios = ua.match(/OS (\d+[._]\d+)/i);
      return ios ? `ОС: iOS ${ios[1].replace(/_/g, ".")}${archSuffix}` : `ОС: iOS${archSuffix}`;
    }
    if (/CrOS/i.test(ua)) return `ОС: Chrome OS${archSuffix}`;
    if (/Macintosh|Mac OS X/i.test(ua)) {
      const mv = ua.match(/Mac OS X (\d+[._]\d+(?:[._]\d+)?)/i);
      return mv ? `ОС: macOS ${mv[1].replace(/_/g, ".")}${archSuffix}` : `ОС: macOS${archSuffix}`;
    }
    if (/Linux/i.test(ua)) {
      if (/Kali/i.test(ua)) return `ОС: Linux (Kali)${archSuffix}`;
      if (/Ubuntu/i.test(ua)) return `ОС: Linux (Ubuntu)${archSuffix}`;
      if (/Fedora/i.test(ua)) return `ОС: Linux (Fedora)${archSuffix}`;
      return `ОС: Linux${archSuffix}`;
    }
    if (/Windows/i.test(ua)) return `ОС: Windows${archSuffix}`;
    return "ОС: —";
  }

  async function labelFromClientHints() {
    const ud = navigator.userAgentData;
    if (!ud || typeof ud.getHighEntropyValues !== "function") return null;
    const h = await ud.getHighEntropyValues([
      "platform",
      "platformVersion",
      "architecture",
      "bitness",
    ]);
    const plat = (h.platform || "").trim();
    const pv = (h.platformVersion || "").trim();
    const arch = h.architecture
      ? ` (${h.architecture}${h.bitness ? ", " + h.bitness + "-bit" : ""})`
      : "";

    if (plat === "Windows") {
      const major = parseInt(String(pv).split(".")[0], 10);
      const winName =
        !Number.isNaN(major) && major >= 15 ? "Windows 11" : "Windows 10";
      return `ОС: ${winName}${arch}`;
    }
    if (plat === "Linux") {
      const extra = pv && pv !== "unknown" ? ` ${pv}` : "";
      return `ОС: Linux${extra}${arch}`;
    }
    if (plat === "macOS") {
      const extra =
        pv && pv !== "unknown" ? ` ${String(pv).replace(/_/g, ".")}` : "";
      return `ОС: macOS${extra}${arch}`;
    }
    if (plat === "Android") {
      return `ОС: Android${pv && pv !== "unknown" ? " " + pv : ""}${arch}`;
    }
    if (plat) {
      return `ОС: ${plat}${
        pv && pv !== "unknown" ? " " + pv : ""
      }${arch}`;
    }
    return null;
  }

  function isLocalHost() {
    const h = location.hostname || "";
    return (
      h === "localhost" ||
      h === "127.0.0.1" ||
      h === "[::1]" ||
      h === "::1"
    );
  }

  async function labelFromServer() {
    const res = await fetch("/api/ui/host-os", { credentials: "same-origin" });
    if (!res.ok) return null;
    const d = await res.json().catch(() => null);
    if (!d || d.error) return null;
    const sys = (d.system || "").trim();
    const rel = (d.release || "").trim();
    const mach = (d.machine || "").trim();
    if (!sys && !rel) return null;
    const core = [sys, rel].filter(Boolean).join(" ");
    return mach ? `ОС: ${core} (${mach})` : `ОС: ${core}`;
  }

  async function run() {
    const el = document.getElementById("header-system");
    if (!el) return;
    if (isLocalHost()) {
      try {
        const srv = await labelFromServer();
        if (srv) {
          el.textContent = srv;
          return;
        }
      } catch (_) {
        /* fallback ниже */
      }
    }
    try {
      const ch = await labelFromClientHints();
      if (ch) {
        el.textContent = ch;
        return;
      }
    } catch (_) {
      /* fallback */
    }
    el.textContent = fallbackFromUa(navigator.userAgent || "");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => void run());
  } else {
    void run();
  }
})();
