from http.server import BaseHTTPRequestHandler, HTTPServer
import json, os, traceback, io, sys

POP = {}
try:
    with open("NewLanguageRishi.py", "r", encoding="utf-8") as f:
        code_text = f.read()
    idx = code_text.rfind('\nbuf=""\n')
    if idx != -1:
        code_text = code_text[:idx]
    exec(code_text, POP)
    print("Loaded OK")
    print("run_block in POP:", 'run_block' in POP)
    print("run_action in POP:", 'run_action' in POP)
    print("run_code in POP:", 'run_code' in POP)
except Exception as e:
    print("Load error:", e)
    traceback.print_exc()

def silent_clear():
    try:
        if isinstance(POP.get('memory'), dict): POP['memory'].clear()
        if isinstance(POP.get('FUNCTIONS'), dict): POP['FUNCTIONS'].clear()
        if isinstance(POP.get('MAIN_BODIES'), list): POP['MAIN_BODIES'].clear()
    except Exception as e:
        print("Clear error:", e)

def run_pop_code(code):
    print(f"DEBUG RECEIVED: {repr(code)}", flush=True)
    code = code.strip()
    if not code:
        return "(empty code received)"
    if code.strip() in ("clear.", "clear"):
        silent_clear()
        return "[session deleted - fresh start]"
    if code.strip() in ("run.", "run"):
        if POP.get('MAIN_BODIES'):
            try:
                _, merged = POP['FUNCTIONS']['main']
                for s in POP['get_stmts'](merged):
                    POP['run_action'](s)
            except Exception as e:
                print("Error in main:", e)
        return None
    lines = code.split('\n')
    buf = ""
    for raw_line in lines:
        line = raw_line.strip()
        if not line: continue
        buf = line if not buf else buf + "\n" + line
        if buf.count('{') > buf.count('}'): continue
        if buf.strip().endswith(','): continue
        chunk = buf.strip()
        buf = ""
        print(f"DEBUG RUNNING CHUNK: {repr(chunk)}", flush=True)
        try:
            if 'run_block' in POP and callable(POP['run_block']):
                POP['run_block'](chunk)
                print(f"DEBUG run_block OK, memory={POP.get('memory')}", flush=True)
            elif 'run_action' in POP:
                if chunk.endswith('.'): chunk = chunk[:-1]
                POP['run_action'](chunk)
            else:
                print("DEBUG: NO run_block / run_action in POP!", flush=True)
        except Exception as e:
            print(f"DEBUG ERROR in chunk: {e}", flush=True)
            traceback.print_exc()
    if buf.strip():
        try: POP['run_block'](buf)
        except Exception as e: print(f"DEBUG ERROR leftover: {e}", flush=True)
    return None

class Handler(BaseHTTPRequestHandler):
    def _send(self, text, code=200, ctype="text/html"):
        data = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        path = self.path
        if path == "/": path = "/index.html"
        filename = path.lstrip("/")
        if filename in ["index.html", "style.css", "script.js"]:
            if os.path.exists(filename):
                ctype = "text/html"
                if filename.endswith(".css"): ctype = "text/css"
                if filename.endswith(".js"): ctype = "application/javascript"
                with open(filename, "r", encoding="utf-8") as f:
                    self._send(f.read(), 200, ctype)
                return
        if path == "/clear":
            silent_clear()
            self._send(json.dumps({"output": "[session deleted - fresh start]"}), 200, "application/json")
            return
        self._send("Not found", 404, "text/plain")
    def do_POST(self):
        if self.path == "/run":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()
            try:
                data = json.loads(body)
                code = data.get("code", "")
            except:
                code = body
            try:
                old_stdout = sys.stdout
                sys.stdout = io.StringIO()
                try:
                    result = run_pop_code(code)
                    printed = sys.stdout.getvalue()
                finally:
                    sys.stdout = old_stdout
                output = printed
                if result is not None and str(result).strip() != "":
                    output += str(result)
                if output.strip() == "":
                    output = "(no output)"
                silent_clear()
                self._send(json.dumps({"output": output}), 200, "application/json")
            except Exception as e:
                traceback.print_exc()
                silent_clear()
                self._send(json.dumps({"output": f"Error: {e}"}), 200, "application/json")
            return
        if self.path == "/clear":
            silent_clear()
            self._send(json.dumps({"output": "[session deleted - fresh start]"}), 200, "application/json")
            return
        self._send("Not found", 404, "text/plain")
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"POP Server running on http://localhost:{port}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
