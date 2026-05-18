/*
 * Paste this whole snippet into your browser's DevTools Console while
 * logged in at https://www.skoob.com.br/ , then click any shelf in the
 * left sidebar (Lido / Lendo / Quero ler ...).
 *
 * Your token is printed to the console AND copied to your clipboard.
 * Copy the value that comes after "SKOOB JWT:" into your .env file.
 *
 * Why this is needed: Skoob holds the session in an HttpOnly cookie, so
 * JavaScript cannot read the token from storage. The only reliable way
 * to get it is to observe one outgoing API request, which is all this
 * does. It is read-only: it never sends, modifies, or stores anything.
 */
(() => {
  const orig = window.fetch;
  window.fetch = function (...args) {
    try {
      const url = (typeof args[0] === "string") ? args[0] : args[0]?.url;
      const hdrs = args[1]?.headers || {};
      if (String(url).includes("prd-api.skoob.com.br")) {
        const auth = hdrs.Authorization || hdrs.authorization;
        if (auth) {
          console.log("SKOOB JWT:", auth);
          navigator.clipboard.writeText(String(auth)).catch(() => {});
          window.fetch = orig; // self-uninstall after first capture
        }
      }
    } catch (e) {}
    return orig.apply(this, args);
  };
  console.log("Interceptor armed. Now click any shelf in the sidebar.");
})();
