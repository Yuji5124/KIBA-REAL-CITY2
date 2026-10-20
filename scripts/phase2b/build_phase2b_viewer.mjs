import { cp, mkdir, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const projectRoot = [root, path.dirname(root)].find((candidate) => candidate.endsWith('kiba-park-phase2b') || candidate.endsWith('KIBA-REAL-CITY'));
if (!projectRoot) throw new Error(`Cannot locate Phase 2B project root from ${root}`);
const out = path.join(projectRoot, 'build-phase2b');
await rm(out, { recursive: true, force: true });
await mkdir(path.join(out, 'data', 'processed', 'phase2b'), { recursive: true });
await mkdir(path.join(out, 'reports', 'phase2b'), { recursive: true });
await cp(path.join(projectRoot, 'web', 'phase2b'), path.join(out, 'web', 'phase2b'), { recursive: true });
await cp(path.join(projectRoot, 'data', 'processed', 'phase2b', 'phase2b_scene.json'), path.join(out, 'data', 'processed', 'phase2b', 'phase2b_scene.json'));
await cp(path.join(projectRoot, 'reports', 'phase2b', 'phase2b_report.json'), path.join(out, 'reports', 'phase2b', 'phase2b_report.json'));
await cp(path.join(projectRoot, 'reports', 'phase2b', 'browser-performance.json'), path.join(out, 'reports', 'phase2b', 'browser-performance.json'));
console.log(`Phase 2B viewer built at ${out}`);
