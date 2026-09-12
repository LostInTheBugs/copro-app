/**
 * Pont de téléchargement pour la version de bureau (WebView pywebview).
 *
 * La WebView Windows n'exécute pas les téléchargements des liens vers
 * l'API locale (exports PDF/CSV : quittances, compte de gestion, rapport
 * annuel, PV, documents…). En mode bureau, les clics sur ces liens sont
 * interceptés : fetch du contenu, puis « Enregistrer sous » natif via
 * window.pywebview.api.save_file. En navigateur, rien ne change.
 */

declare global {
  interface Window {
    pywebview?: {
      api?: {
        save_file: (
          filename: string,
          content: string,
          binary?: boolean,
          path?: string
        ) => Promise<{ ok: boolean; path?: string; cancelled?: boolean; error?: string }>;
      };
    };
  }
}

export function isDesktop(): boolean {
  return typeof window !== "undefined" && !!window.pywebview?.api;
}

function toBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let bin = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    bin += String.fromCharCode(...Array.from(bytes.subarray(i, i + chunk)));
  }
  return btoa(bin);
}

export function installDesktopDownloadBridge(): void {
  if (!isDesktop()) return;
  document.addEventListener(
    "click",
    async (ev) => {
      const target = ev.target as HTMLElement | null;
      const a = target?.closest?.("a");
      if (!a) return;
      const href = a.getAttribute("href") || "";
      if (!href.startsWith("/api/")) return; // uniquement les téléchargements de l'API locale
      ev.preventDefault();
      ev.stopPropagation();
      try {
        const res = await fetch(href);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const blob = await res.blob();
        const cd = res.headers.get("content-disposition") || "";
        const m = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cd);
        const name =
          (m ? decodeURIComponent(m[1]) : "") ||
          href.split("?")[0].split("/").pop() ||
          "export";
        const r = await window.pywebview!.api!.save_file(
          name,
          toBase64(await blob.arrayBuffer()),
          true
        );
        if (r.cancelled) return;
        if (!r.ok) alert("Export impossible : " + (r.error || "erreur inconnue"));
      } catch (e) {
        alert("Export impossible : " + (e instanceof Error ? e.message : String(e)));
      }
    },
    true
  );
}
