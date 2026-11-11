# app.py - POP Server, only built-in Python, no Flask, no pip
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import traceback
import io
import sys

# Load YOUR core file WITHOUT running its REPL
# Load YOUR core file WITHOUT running its REPL
POP = {}
try:
    with open("NewLanguageRishi.py", "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Keep only lines BEFORE the REPL starts
    # Stop at the first line that contains the REPL marker
    clean_lines = []
    for line in lines:
        if 'POP with funcs' in line:
            break
        # Also stop if we see the REPL loop starting
        if 'while True' in line and 'POP' in line:
            break
        clean_lines.append(line)
    pop_code = "".join(clean_lines)
    # Safety: if last line is a broken print(, drop it
    if pop_code.rstrip().endswith('print("'):
        pop_code = pop_code.rstrip()[:-8]
    exec(pop_code, POP)
    print("Loaded NewLanguageRishi.py libraries (REPL skipped)")
except Exception as e:
    print(f"Error loading NewLanguageRishi.py: {e}")
    traceback.print_exc()

def run_pop_code(code):
    for name in ['run_block', 'run_code', 'run', 'execute']:
        if name in POP and callable(POP[name]):
            return POP[name](code)
    return "Error: Could not find run_block / run_code in NewLanguageRishi.py"

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
        # Serve index.html, style.css, script.js
        path = self.path
        if path == "/":
            path = "/index.html"
        filename = path.lstrip("/")
        if filename in ["index.html", "style.css", "script.js"]:
            if os.path.exists(filename):
                ctype = "text/html"
                if filename.endswith(".css"):
                    ctype = "text/css"
                if filename.endswith(".js"):
                    ctype = "application/javascript"
                with open(filename, "r", encoding="utf-8") as f:
                    self._send(f.read(), 200, ctype)
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
                self._send(json.dumps({"output": output}), 200, "application/json")
            except Exception as e:
                traceback.print_exc()
                self._send(json.dumps({"output": f"Error: {e}"}), 200, "application/json")
        else:
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
    print("Your libraries from NewLanguageRishi.py are loaded.")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()