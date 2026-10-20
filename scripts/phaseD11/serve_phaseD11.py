from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import os

ROOT=Path(__file__).resolve().parents[2]
SHOTS=ROOT/'screenshots/phaseD11'
ALLOWED={'d11_after_start.png','d11_midcourse.png','d11_turnaround.png','d11_return.png'}
class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        prefix='/__phaseD11_screenshot__/'
        name=self.path.removeprefix(prefix)
        if not self.path.startswith(prefix) or name not in ALLOWED:
            self.send_error(404);return
        data=self.rfile.read(int(self.headers.get('Content-Length','0')))
        if len(data)<100 or not data.startswith(b'\x89PNG\r\n\x1a\n'):
            self.send_error(400,'PNG required');return
        SHOTS.mkdir(parents=True,exist_ok=True);(SHOTS/name).write_bytes(data)
        self.send_response(201);self.end_headers();self.wfile.write(b'saved')
    def log_message(self,*args):pass
os.chdir(ROOT/'build-phaseD11')
print('KIBA PARK DRIVE Phase D1.1: http://127.0.0.1:8786/web/phaseD11/',flush=True)
ThreadingHTTPServer(('127.0.0.1',8786),Handler).serve_forever()
