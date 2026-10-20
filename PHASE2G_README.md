# Kiba Park Rebuild Phase 2G

## Rebuild
From the repository root in Windows PowerShell:
python scripts\phase2g\build_phase2g.py
python scripts\phase2g\verify_phase2g.py
python scripts\phase2g\serve_phase2g.py

Open http://127.0.0.1:8780/web/phase2g/ and stop the server with Ctrl+C. The viewer copies Phase 2F web/data into build-phase2g, then adds visual-only underside/curb/guardrail meshes from mapped Phase 2F surface quads.

All Phase 2G dimensions are estimates. Navigation stays byte-identical to Phase 2C, and collision/traversal are disabled. The 16.609m boundary-clipped span remains visual-only and receives no Phase 2G rails or underdeck details.
