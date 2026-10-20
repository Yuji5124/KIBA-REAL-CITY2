import { cp, mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const build = resolve(root, 'build');
await mkdir(resolve(build, 'web/phase1-threejs'), { recursive: true });
await mkdir(resolve(build, 'data/processed'), { recursive: true });
await cp(resolve(root, 'web/phase1-threejs'), resolve(build, 'web/phase1-threejs'), { recursive: true, force: true });
await cp(resolve(root, 'data/processed/phase1_threejs'), resolve(build, 'data/processed/phase1_threejs'), { recursive: true, force: true });
console.log(`Static viewer built at ${build}`);
