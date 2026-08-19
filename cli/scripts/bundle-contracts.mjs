// Copy the published JSON schemas next to the built CLI.
//
// The CLI validates against the same files the backend does; a copy checked into
// this package would be free to drift from them, and the first thing to notice
// would be a plan that lints here and is rejected there.
import { cp, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const source = join(dirname(packageRoot), "contracts");
const destination = join(packageRoot, "contracts");

await mkdir(destination, { recursive: true });
await cp(source, destination, { recursive: true });
console.error(`bundled contracts from ${source}`);
