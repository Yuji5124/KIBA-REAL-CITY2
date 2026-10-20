from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; WEB=ROOT/'build-phase2f'; OUT=ROOT/'screenshots'/'phase2f'
ALLOWED={'phase2e_before_top.png','phase2f_top.png','phase2f_bridge.png','phase2f_side.png','phase2f_robot.png'}
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(WEB),**kwargs)
 def do_POST(self):
  name=self.path.rsplit('/',1)[-1]
  if not self.path.startswith('/__phase2f_screenshot__/') or name not in ALLOWED: self.send_error(404); return
  n=int(self.headers.get('Content-Length','0'))
  if n<8 or n>15_000_000: self.send_error(413); return
  data=self.rfile.read(n)
  if not data.startswith(b'\x89PNG\r\n\x1a\n'): self.send_error(415); return
  OUT.mkdir(parents=True,exist_ok=True); (OUT/name).write_bytes(data)
  self.send_response(201); self.end_headers(); self.wfile.write(f'saved {name}'.encode())
if __name__=='__main__':
 print(f'Serving {WEB} at http://127.0.0.1:8779'); ThreadingHTTPServer(('127.0.0.1',8779),Handler).serve_forever()
