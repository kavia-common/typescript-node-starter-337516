"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const mathematic_1 = require("./mathematic");
const server_1 = require("./server");
console.log('minimal typescript starter');
console.log(`The answer is: ${mathematic_1.Mathematic.add(2, 3)}`);
(0, server_1.startServerFromEnv)()
    .then(({ host, port, healthcheckPath }) => {
    console.log(`HTTP server listening on http://${host}:${port} (health: ${healthcheckPath})`);
})
    .catch((err) => {
    console.error('Failed to start HTTP server:', err);
    process.exit(1);
});
//# sourceMappingURL=index.js.map