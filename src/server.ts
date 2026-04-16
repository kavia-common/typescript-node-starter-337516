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
  const host = process.env.HOST ?? '0.0.0.0';
  const port = Number(process.env.PORT ?? '3001');
  const healthcheckPath = normalizeHealthcheckPath(process.env.HEALTHCHECK_PATH ?? '/healthz');

  return new Promise((resolve, reject) => {
    const server = http.createServer((req: IncomingMessage, res: ServerResponse) => {
      const method = (req.method ?? 'GET').toUpperCase();
      const path = requestPath(req);

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
