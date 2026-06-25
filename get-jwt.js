/*
 * Paste this whole snippet into your browser's DevTools Console while
 * logged in at https://www.skoob.com.br/ , then click any shelf in the
 * left sidebar (Lido / Lendo / Quero ler ...) or reload your shelf page.
 *
 * Your token is printed to the console AND copied to your clipboard.
 * Copy the value that comes after "SKOOB JWT:" into your .env file.
 *
 * Why this is needed: Skoob holds the session in an HttpOnly cookie, so
 * JavaScript cannot read the token from storage. The only reliable way
 * to get it is to observe one outgoing API request, which is all this
 * does. It is read-only: it never sends, modifies, or stores anything.
 *
 * IMPORTANT: if you have an ad-blocker / privacy extension (uBlock,
 * Brave Shields, Privacy Badger, AdGuard, ...), it may block requests to
 * `prd-api.skoob.com.br`. You will see `net::ERR_BLOCKED_BY_CLIENT` and
 * your shelf page will show "Ops, algo deu errado". If so, allow that
 * host (or disable the blocker for skoob.com.br) before running this,
 * otherwise NO request is made and there is nothing to capture.
 */
(() => {
  // Pull the Authorization value out of whatever shape headers arrive in:
  // a plain object, a Headers instance, or a Request object.
  const readAuth = (input, init) => {
    const fromHeaders = (h) => {
      if (!h) return null;
      if (typeof h.get === "function") return h.get("authorization"); // Headers instance
      // plain object — match case-insensitively
      for (const k in h) if (k.toLowerCase() === "authorization") return h[k];
      return null;
    };
    return (
      fromHeaders(init && init.headers) ||
      (input && input.headers ? fromHeaders(input.headers) : null) // Request object
    );
  };

  const report = (auth) => {
    if (!auth || window.__skoobJwtCaptured) return;
    window.__skoobJwtCaptured = true;
    const token = String(auth).replace(/^Bearer\s+/i, "").trim();
    console.log("SKOOB JWT:", token);
    if (navigator.clipboard) {
      navigator.clipboard.writeText(token).catch(() => {});
    }
    console.log("Copied to clipboard. Paste it after SKOOB_JWT= in your .env file.");
  };

  const isApi = (url) => String(url).includes("prd-api.skoob.com.br");

  // 1) Hook fetch
  const origFetch = window.fetch;
  window.fetch = function (input, init) {
    try {
      const url = typeof input === "string" ? input : input && input.url;
      if (isApi(url)) report(readAuth(input, init));
    } catch (e) {}
    return origFetch.apply(this, arguments);
  };

  // 2) Hook XMLHttpRequest (in case Skoob uses XHR for some calls)
  const origOpen = XMLHttpRequest.prototype.open;
  const origSetHeader = XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.open = function () {
    this.__skoobIsApi = isApi(arguments[1]); // arguments: (method, url, ...)
    return origOpen.apply(this, arguments);
  };
  XMLHttpRequest.prototype.setRequestHeader = function (name, value) {
    try {
      if (this.__skoobIsApi && String(name).toLowerCase() === "authorization") {
        report(value);
      }
    } catch (e) {}
    return origSetHeader.apply(this, arguments);
  };

  console.log(
    "Interceptor armed (fetch + XHR). Now click any shelf in the sidebar, " +
      "or reload your shelf page. If you see ERR_BLOCKED_BY_CLIENT, an " +
      "extension is blocking prd-api.skoob.com.br — allow it and retry."
  );
})();
