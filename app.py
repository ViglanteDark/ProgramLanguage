# app.py - POP Server, only built-in Python, no Flask, no pip
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import traceback
import io
import sys

# Load YOUR core file WITHOUT running its REPL
POP = {}
try:
    with open("NewLanguageRishi.py", "r", encoding="utf-8") as f:
        lines = f.readlines()
    clean_lines = []
    for line in lines:
        if 'POP with funcs' in line:
            break
        clean_lines.append(line)
    pop_code = "".join(clean_lines)
    exec(pop_code, POP)
    print("Loaded NewLanguageRishi.py libraries (REPL skipped)")
    print("Has run_code:", 'run_code' in POP, "Has clear_session:", 'clear_session' in POP)
except Exception as e:
    print(f"Error loading NewLanguageRishi.py: {e}")
    traceback.print_exc()

def silent_clear():
    # Delete session WITHOUT printing "[session deleted]" into output
    try:
        if 'memory' in POP and isinstance(POP['memory'], dict):
            POP['memory'].clear()
        if 'FUNCTIONS' in POP and isinstance(POP['FUNCTIONS'], dict):
            POP['FUNCTIONS'].clear()
        if 'MAIN_BODIES' in POP and isinstance(POP['MAIN_BODIES'], list):
            POP['MAIN_BODIES'].clear()
    except Exception as e:
        print("Clear error:", e)

def run_pop_code(code):
    # FIX: Use run_code for multiline, NOT run_block
    # run_code handles: multiline, comma, { } blocks, functions
    if 'run_code' in POP and callable(POP['run_code']):
        return POP['run_code'](code)
    if 'run_block' in POP and callable(POP['run_block']):
        # Fallback: split lines and run each
        for line in code.split('\n'):
            line = line.strip()
            if line:
                POP['run_block'](line)
        return None
    return "Error: Could not find run_code / run_block in NewLanguageRishi.py"

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
        # NEW: GET /clear also works
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
                # === DELETE SESSION AFTER EACH USE ===
                # So next run sees everything fresh, no old variables
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
    print("Your libraries from NewLanguageRishi.py are loaded.")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
