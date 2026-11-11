def run_code(text):
    # split by newline, but keep { } blocks together
    lines = text.split('\n')
    buf2 = ""
    for line in lines:
        line = line.strip()
        if not line: continue
        buf2 = line if not buf2 else buf2 + "\n" + line
        if buf2.count('{') > buf2.count('}'):
            continue
        if buf2.strip().endswith(','):
            continue
        if buf2.strip().endswith('.') or buf2.strip().endswith('='):
            try: run_block(buf2)
            except Exception as e: print("Error:", e)
            buf2 = ""
        # if no dot, still run it as one statement (for multiline without dots)
        elif buf2.count('{') == buf2.count('}'):
            try: run_block(buf2 + '.')
            except Exception as e: print("Error:", e)
            buf2 = ""

buf=""
print("POP with funcs - F/Func/func, main merges if MERGE_MAINS=True")
print("Type 'run.' to run main if defined")
print("Paste multiline code, then press Enter on empty line to run all")

while True:
    c=input(">> " if not buf else ".. ")
    if c.strip()=="exit": break
    if c.strip()=="clear." or c.strip()=="clear":
        memory.clear(); FUNCTIONS.clear(); MAIN_BODIES.clear()
        print("[session deleted - fresh start]")
        buf=""; continue
    if c.strip()=="run." or c.strip()=="run":
        if MAIN_BODIES:
            try:
                _, merged = FUNCTIONS['main']
                for s in get_stmts(merged): run_action(s)
            except ReturnValue: pass
            except Exception as e: print("Error in main:",e)
        else:
            print("No main - top-level code already runs")
        continue
    if c.strip()=="" and buf:
        # empty line = run everything pasted
        run_code(buf)
        buf=""
        continue
    buf=c if not buf else buf+"\n"+c
    if buf.count('{')>buf.count('}'): continue
    if buf.strip().endswith(','): continue
    # DON'T run immediately if more lines coming - wait for empty line OR dot + next line?
    # For single line quick test, if it ends with . and no {, run it
    if buf.strip().endswith('.') and '\n' not in buf.strip():
        try: run_block(buf)
        except Exception as e: print("Error:",e)
        buf=""
