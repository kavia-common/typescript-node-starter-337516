import http, { IncomingMessage, Server, ServerResponse } from 'http';
import { URL } from 'url';

type StartServerResult = {
  server: Server;
  host: string;
  port: number;
  healthcheckPath: string;
};

function normalizeHealthcheckPath(path: string): string {
  // Ensure leading slash and avoid empty path.
  const trimmed = path.trim();
  if (!trimmed) return '/healthz';
  return trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
}

function requestPath(req: IncomingMessage): string {
  const rawUrl = req.url ?? '/';
  // Ensure URL parsing works even if req.url is path-only.
  const parsed = new URL(rawUrl, 'http://localhost');
  return parsed.pathname;
}

/**
 * PUBLIC_INTERFACE
 * Starts a minimal HTTP server that binds to HOST/PORT and exposes a healthcheck endpoint.
 *
 * This repo originally was a CLI-only TypeScript starter that did not listen on any TCP port.
 * Kavia PreviewManager expects backend containers to bind to the allocated <port> (3001 here),
 * otherwise the preview will never become "ready".
 *
 * Environment variables used:
 * - HOST (default: "0.0.0.0")
 * - PORT (default: 3001)
 * - HEALTHCHECK_PATH (default: "/healthz")
 */
export function startServerFromEnv(): Promise<StartServerResult> {
  const host = (process.env.HOST ?? '').trim() || '0.0.0.0';
  // Be defensive: PreviewManager always provides PORT, but if it's malformed we still want
  // to bind to a sensible default instead of crashing or listening on NaN.
  const parsedPort = Number.parseInt((process.env.PORT ?? '').trim(), 10);
  const port =
    Number.isFinite(parsedPort) && parsedPort > 0 ? parsedPort : 3001;
  const healthcheckPath = normalizeHealthcheckPath(
    process.env.HEALTHCHECK_PATH ?? '/healthz'
  );

  return new Promise((resolve, reject) => {
    const server = http.createServer(
      (req: IncomingMessage, res: ServerResponse) => {
        const method = (req.method ?? 'GET').toUpperCase();
        const path = requestPath(req);

        // Kavia preview for backend containers commonly points at /docs (see work item URL),
        // so provide a lightweight docs page to avoid "not_found" in preview.
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

        // Minimal OpenAPI document so platform tooling that expects /openapi.json has something valid.
        if (method === 'GET' && path === '/openapi.json') {
          res.statusCode = 200;
          res.setHeader('Content-Type', 'application/json; charset=utf-8');
          res.end(
            JSON.stringify(
              {
                openapi: '3.0.0',
                info: {
                  title: 'TypeScript Node Starter API',
                  version: '1.0.0',
                  description:
                    'Minimal HTTP endpoints for container readiness / preview.',
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
              },
              null,
              2
            )
          );
          return;
        }

        // Health check endpoint used by platform readiness probes.
        if (method === 'GET' && path === healthcheckPath) {
          res.statusCode = 200;
          res.setHeader('Content-Type', 'text/plain; charset=utf-8');
          res.end('ok');
          return;
        }

        // Basic root response so humans can quickly verify the service is up.
        if (method === 'GET' && path === '/') {
          res.statusCode = 200;
          res.setHeader('Content-Type', 'application/json; charset=utf-8');
          res.end(
            JSON.stringify({
              status: 'up',
              docs: '/docs',
              healthcheck: healthcheckPath,
            })
          );
          return;
        }

        res.statusCode = 404;
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({ error: 'not_found' }));
      }
    );

    server.once('error', (err) => {
      reject(err);
    });

    server.listen(port, host, () => {
      resolve({ server, host, port, healthcheckPath });
    });
  });
}
