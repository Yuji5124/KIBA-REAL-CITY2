from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build-phaseD3"
SHOTS = ROOT / "screenshots"
PORT = 8788
ALLOWED = {f"d3_{course}_{state}.png" for course in ("a", "b") for state in ("start", "midcourse", "checkpoint", "goal")} | {"d3_candidates.png"}


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        prefix = "/__phaseD3_screenshot__/"
        name = self.path.removeprefix(prefix)
        if not self.path.startswith(prefix) or name not in ALLOWED:
            self.send_error(404)
            return
        data = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        if len(data) < 100 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
            self.send_error(400, "PNG required")
            return
        SHOTS.mkdir(parents=True, exist_ok=True)
        (SHOTS / name).write_bytes(data)
        self.send_response(201)
        self.end_headers()
        self.wfile.write(b"saved")

    def log_message(self, *_args):
        pass


if not (BUILD / "web/phaseD3/index.html").is_file():
    raise SystemExit(f"Phase D3 build missing: {BUILD}")
os.chdir(BUILD)
print(f"KIBA PARK DRIVE Phase D3: http://127.0.0.1:{PORT}/web/phaseD3/", flush=True)
ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
