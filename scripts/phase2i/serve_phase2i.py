from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / 'screenshots/phase2i'
ALLOWED = {'phase2i_off.png', 'phase2i_top.png', 'phase2i_bridge.png', 'phase2i_side.png', 'phase2i_robot.png'}

class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        prefix = '/__phase2i_screenshot__/'
        name = self.path.removeprefix(prefix)
        if not self.path.startswith(prefix) or name not in ALLOWED:
            self.send_error(404); return
        data = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        if len(data) < 100 or not data.startswith(b'\x89PNG\r\n\x1a\n'):
            self.send_error(400, 'PNG required'); return
        SHOTS.mkdir(parents=True, exist_ok=True); (SHOTS / name).write_bytes(data)
        self.send_response(201); self.end_headers(); self.wfile.write(b'saved')
    def log_message(self, *args): pass

os.chdir(ROOT / 'build-phase2i')
print('Phase2I viewer: http://127.0.0.1:8782/web/phase2i/', flush=True)
ThreadingHTTPServer(('127.0.0.1', 8782), Handler).serve_forever()
