import { Mathematic } from './mathematic';
import { startServerFromEnv } from './server';

// eslint-disable-next-line no-console
console.log('minimal typescript starter');

// eslint-disable-next-line no-console
console.log(`The answer is: ${Mathematic.add(2, 3)}`);

// Start an HTTP server so PreviewManager can detect that the container is ready on <port>.
startServerFromEnv()
  .then(({ host, port, healthcheckPath }) => {
    // eslint-disable-next-line no-console
    console.log(`HTTP server listening on http://${host}:${port} (health: ${healthcheckPath})`);
  })
  .catch((err: unknown) => {
    // eslint-disable-next-line no-console
    console.error('Failed to start HTTP server:', err);
    process.exit(1);
  });
