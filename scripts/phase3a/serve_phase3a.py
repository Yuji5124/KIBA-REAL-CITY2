from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os

ROOT=Path(__file__).resolve().parents[2]
SHOTS=ROOT/'screenshots/phase3a'
ALLOWED={'phase3a_top.png','phase3a_game.png'}
class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        prefix='/__phase3a_screenshot__/'
        name=self.path.removeprefix(prefix)
        if not self.path.startswith(prefix) or name not in ALLOWED:
            self.send_error(404); return
        payload=self.rfile.read(int(self.headers.get('Content-Length','0')))
        if len(payload)<100 or not payload.startswith(b'\x89PNG\r\n\x1a\n'):
            self.send_error(400,'PNG required'); return
        SHOTS.mkdir(parents=True,exist_ok=True); (SHOTS/name).write_bytes(payload)
        self.send_response(201); self.end_headers(); self.wfile.write(b'saved')
    def log_message(self,*args): pass
os.chdir(ROOT/'build-phase3a')
print('Phase 3A viewer: http://127.0.0.1:8784/web/phase3a/',flush=True)
ThreadingHTTPServer(('127.0.0.1',8784),Handler).serve_forever()
