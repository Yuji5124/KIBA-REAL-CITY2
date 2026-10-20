import { cp, mkdir, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(scriptDir, '../..');
const sourceRoot = process.env.KIBA_PHASE2_SOURCE_ROOT || root;
const out = path.join(root, 'build-phase2c');
await rm(out, { recursive: true, force: true });
await mkdir(out, { recursive: true });
for (const rel of ['web/phase2c', 'data/processed/phase2c', 'reports/phase2c'])
  await cp(path.join(root, rel), path.join(out, rel), { recursive: true });
await cp(path.join(sourceRoot, 'data/processed/phase2b'), path.join(out, 'data/processed/phase2b'), { recursive: true });
console.log(`Phase 2C viewer assembled: ${out}`);
