"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.startServerFromEnv = void 0;
const http_1 = __importDefault(require("http"));
const url_1 = require("url");
function normalizeHealthcheckPath(path) {
    const trimmed = path.trim();
    if (!trimmed)
        return '/healthz';
    return trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
}
function requestPath(req) {
    var _a;
    const rawUrl = (_a = req.url) !== null && _a !== void 0 ? _a : '/';
    const parsed = new url_1.URL(rawUrl, 'http://localhost');
    return parsed.pathname;
}
function startServerFromEnv() {
    var _a, _b, _c;
    const host = ((_a = process.env.HOST) !== null && _a !== void 0 ? _a : '').trim() || '0.0.0.0';
    const parsedPort = Number.parseInt(((_b = process.env.PORT) !== null && _b !== void 0 ? _b : '').trim(), 10);
    const port = Number.isFinite(parsedPort) && parsedPort > 0 ? parsedPort : 3001;
    const healthcheckPath = normalizeHealthcheckPath((_c = process.env.HEALTHCHECK_PATH) !== null && _c !== void 0 ? _c : '/healthz');
    return new Promise((resolve, reject) => {
        const server = http_1.default.createServer((req, res) => {
            var _a;
            const method = ((_a = req.method) !== null && _a !== void 0 ? _a : 'GET').toUpperCase();
            const path = requestPath(req);
            if (method === 'GET' && (path === '/docs' || path === '/docs/')) {
                res.statusCode = 200;
                res.setHeader('Content-Type', 'text/html; charset=utf-8');
                res.end(`<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>TypeScript Node Starter – Docs</title>
    <style>
      body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial; line-height: 1.4; margin: 24px; }
      code { background: #f4f4f5; padding: 2px 6px; border-radius: 4px; }
      a { color: #2563eb; }
    </style>
  </head>
  <body>
    <h1>TypeScript Node Starter</h1>
    <p>This is a minimal HTTP server added so PreviewManager can detect readiness.</p>
    <h2>Endpoints</h2>
    <ul>
      <li><code>GET /</code> – basic status JSON</li>
      <li><code>GET ${healthcheckPath}</code> – healthcheck (returns <code>ok</code>)</li>
      <li><code>GET /openapi.json</code> – minimal OpenAPI document</li>
    </ul>
    <p>
      Quick links:
      <a href="/">/</a> ·
      <a href="${healthcheckPath}">${healthcheckPath}</a> ·
      <a href="/openapi.json">/openapi.json</a>
    </p>
  </body>
</html>`);
                return;
            }
            if (method === 'GET' && path === '/openapi.json') {
                res.statusCode = 200;
                res.setHeader('Content-Type', 'application/json; charset=utf-8');
                res.end(JSON.stringify({
                    openapi: '3.0.0',
                    info: {
                        title: 'TypeScript Node Starter API',
                        version: '1.0.0',
                        description: 'Minimal HTTP endpoints for container readiness / preview.',
                    },
                    paths: {
                        '/': {
                            get: {
                                summary: 'Service status',
                                responses: { '200': { description: 'OK' } },
                            },
                        },
                        [healthcheckPath]: {
                            get: {
                                summary: 'Healthcheck',
                                responses: { '200': { description: 'OK' } },
                            },
                        },
                        '/docs': {
                            get: {
                                summary: 'Docs',
                                responses: { '200': { description: 'OK' } },
                            },
                        },
                    },
                }, null, 2));
                return;
            }
            if (method === 'GET' && path === healthcheckPath) {
                res.statusCode = 200;
                res.setHeader('Content-Type', 'text/plain; charset=utf-8');
                res.end('ok');
                return;
            }
            if (method === 'GET' && path === '/') {
                res.statusCode = 200;
                res.setHeader('Content-Type', 'application/json; charset=utf-8');
                res.end(JSON.stringify({
                    status: 'up',
                    docs: '/docs',
                    healthcheck: healthcheckPath,
                }));
                return;
            }
            res.statusCode = 404;
            res.setHeader('Content-Type', 'application/json; charset=utf-8');
            res.end(JSON.stringify({ error: 'not_found' }));
        });
        server.once('error', (err) => {
            reject(err);
        });
        server.listen(port, host, () => {
            resolve({ server, host, port, healthcheckPath });
        });
    });
}
exports.startServerFromEnv = startServerFromEnv;
//# sourceMappingURL=server.js.map