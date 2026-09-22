"""Serve only the teaching-pack download page and published deliverables."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote,urlsplit
import argparse
ROOT=Path(__file__).resolve().parent
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def send_head(self):
        raw=unquote(urlsplit(self.path).path)
        target=(ROOT/raw.lstrip('/')).resolve()
        try:relative=target.relative_to(ROOT)
        except ValueError:self.send_error(403);return None
        if raw in ('/','/index.html'):
            pass
        elif not relative.parts or relative.parts[0] not in ('files','downloads') or not target.is_file():
            self.send_error(404);return None
        return super().send_head()
    def end_headers(self):
        filename=Path(unquote(urlsplit(self.path).path)).name
        if filename.endswith(('.zip','.docx')):
            self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-cache')
        super().end_headers()
    def list_directory(self,path):self.send_error(404);return None
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8080);a=p.parse_args()
    print(f'Teaching pack downloads available on 0.0.0.0:{a.port}',flush=True)
    ThreadingHTTPServer(('0.0.0.0',a.port),Handler).serve_forever()
