"""Download-only server; legacy Batch 1 URLs remain available."""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote,urlsplit
import argparse
ROOT=Path(__file__).resolve().parent
BATCHES={'term1-batch1','term1-batch2-science-b4-b5'}
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def send_head(self):
        raw=unquote(urlsplit(self.path).path)
        if raw in ('/','/index.html'):target=ROOT/'index.html'
        else:
            rel=raw.lstrip('/')
            if rel.startswith(('downloads/','files/')):rel='term1-batch1/'+rel
            target=(ROOT/rel).resolve()
            try:parts=target.relative_to(ROOT).parts
            except ValueError:self.send_error(403);return None
            if len(parts)<3 or parts[0] not in BATCHES or parts[1] not in {'files','downloads'} or not target.is_file():
                self.send_error(404);return None
        self._target=target
        return super().send_head()
    def translate_path(self,path):return str(self._target)
    def end_headers(self):
        filename=Path(unquote(urlsplit(self.path).path)).name
        if filename.endswith(('.zip','.docx')):self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-cache')
        super().end_headers()
    def list_directory(self,path):self.send_error(404);return None
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8080);args=p.parse_args()
    print(f'Teaching-pack catalogue on 0.0.0.0:{args.port}',flush=True)
    ThreadingHTTPServer(('0.0.0.0',args.port),Handler).serve_forever()
