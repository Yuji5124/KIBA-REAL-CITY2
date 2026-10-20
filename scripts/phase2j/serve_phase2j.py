from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os

ROOT=Path(__file__).resolve().parents[2]
SHOTS=ROOT/'screenshots/phase2j'
ALLOWED={'phase2j_top.png','phase2j_bridge.png','phase2j_side.png','phase2j_robot.png'}
class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        prefix='/__phase2j_screenshot__/'
        name=self.path.removeprefix(prefix)
        if not self.path.startswith(prefix) or name not in ALLOWED:
            self.send_error(404); return
        data=self.rfile.read(int(self.headers.get('Content-Length','0')))
        if len(data)<100 or not data.startswith(b'\x89PNG\r\n\x1a\n'):
            self.send_error(400,'PNG required'); return
        SHOTS.mkdir(parents=True,exist_ok=True); (SHOTS/name).write_bytes(data)
        self.send_response(201); self.end_headers(); self.wfile.write(b'saved')
    def log_message(self,*args): pass
os.chdir(ROOT/'build-phase2j')
print('Phase2J viewer: http://127.0.0.1:8783/web/phase2j/',flush=True)
ThreadingHTTPServer(('127.0.0.1',8783),Handler).serve_forever()
