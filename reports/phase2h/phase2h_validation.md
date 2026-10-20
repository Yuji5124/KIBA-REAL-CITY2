# KIBA PARK REBUILD Phase 2H validation

**Result: PASS — isolated browser experiment verified.** The proxy traversed bounded sections only; it did not cross the complete bridge.

## Trial results

| Run | Length | Estimated width | Forward | Reverse | Endpoint |
|---|---:|---:|---:|---:|---|
| A | 68.046 m | 4.0 m | 66.3 m / 663 probes | 66.5 m / 666 probes | BLOCK |
| B | 64.916 m | 4.0 m | 63.2 m / 632 probes | 63.3 m / 635 probes | BLOCK |

The height and width values are estimates. Both ends have a 0.75m experiment guard; this is not a surveyed physical barrier. The 16.609m boundary gap and 100.555m unmodeled extent remain disconnected and blocked. Bridge approaches were not created.

## Navigation preservation

The Phase 2C navigation data is byte-identical to the Phase 2G source (SHA-256 `2a127eff41dce83fb98b3fc725bcc130d060495f3b2c2ffcc27e65bca7578b55`). Its bridge states remain 8 review runs, 5 blocked runs, 0 walkable runs; 760 review and 146 blocked segments. Disabling trial mode hides the trial layer, returns the proxy to its prior park position, and restores the normal-mode bridge-blocked message.

## Browser and performance

Verified in the in-app browser at `http://127.0.0.1:8781/web/phase2h/`. Four 1280×720 images are in `screenshots/phase2h/`. Steady live FPS samples reached 58.1–60.1; capture-time readings varied while changing views and saving screenshots.

| View | Phase 2G FPS / calls / tris / meshes | Phase 2H trial FPS / calls / tris / meshes |
|---|---|---|
| Overhead | 60.1 / 58 / 627,814 / 56 | 60.1 / 62 / 629,090 / 58 |
| Bridge ground | 60.1 / 46 / 552,776 / 56 | 53.2 / 50 / 554,052 / 58 |
| Side | 60.1 / 40 / 552,264 / 56 | 50.2 / 51 / 554,064 / 58 |
| Robot | 60.1 / 19 / 541,188 / 56 | 60.0 / 49 / 630,604 / 58* |

Normal-mode overhead matches Phase 2G. Experimental top and bridge-ground views add 4 calls and 1,276 triangles. The robot-view figures are not directly comparable because the Phase 2H camera starts on the bridge trial run while Phase 2G starts at its default park position.

## Screenshots

- [Overhead](../../screenshots/phase2h/phase2h_top.png)
- [Bridge ground](../../screenshots/phase2h/phase2h_bridge.png)
- [Side](../../screenshots/phase2h/phase2h_side.png)
- [Robot](../../screenshots/phase2h/phase2h_robot.png)

## Windows PowerShell

```powershell
cd C:\Users\hp\Desktop\KIBA-REAL-CITY
python scripts\phase2h\build_phase2h.py
python scripts\phase2h\verify_phase2h.py
python scripts\phase2h\serve_phase2h.py
```

Open `http://127.0.0.1:8781/web/phase2h/`. Enable **実験モード**, select Run A or B, and use forward, reverse, or stop. Disable the mode to return to normal navigation.

## Limits

All deck heights and widths are estimated. The two modeled runs do not connect over the boundary gap, and the 100.555m unmodeled extent remains blocked. No full bridge crossing is represented.
