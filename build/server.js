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
    const host = (_a = process.env.HOST) !== null && _a !== void 0 ? _a : '0.0.0.0';
    const port = Number((_b = process.env.PORT) !== null && _b !== void 0 ? _b : '3001');
    const healthcheckPath = normalizeHealthcheckPath((_c = process.env.HEALTHCHECK_PATH) !== null && _c !== void 0 ? _c : '/healthz');
    return new Promise((resolve, reject) => {
        const server = http_1.default.createServer((req, res) => {
            var _a;
            const method = ((_a = req.method) !== null && _a !== void 0 ? _a : 'GET').toUpperCase();
            const path = requestPath(req);
            if (method === 'GET' && path === healthcheckPath) {
                res.statusCode = 200;
                res.setHeader('Content-Type', 'text/plain; charset=utf-8');
                res.end('ok');
                return;
            }
            if (method === 'GET' && path === '/') {
                res.statusCode = 200;
                res.setHeader('Content-Type', 'application/json; charset=utf-8');
                res.end(JSON.stringify({ status: 'up' }));
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