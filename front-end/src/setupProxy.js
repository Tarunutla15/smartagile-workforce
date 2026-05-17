const { createProxyMiddleware } = require("http-proxy-middleware");

/**
 * Forwards API calls from the CRA dev server (localhost:3000) to Django.
 * Without this, /api/* hits the React app and returns 404.
 */
module.exports = function setupProxy(app) {
  const target = process.env.REACT_APP_PROXY_TARGET || "http://127.0.0.1:8000";

  const apiProxy = createProxyMiddleware({
    target,
    changeOrigin: true,
    secure: false,
    logLevel: "silent",
  });

  app.use("/api", apiProxy);
  app.use("/taskapi", apiProxy);
  app.use("/media", apiProxy);
};
