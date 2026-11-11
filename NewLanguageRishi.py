import re, math as py_math

LEXER_SPEC=[
    ('SKIP', r'[ \t\n]+'),
    ('STRING', r'"[^"]*"'),
    ('FLOAT', r'\d+\.\d+'),
    ('INT', r'\d+'),
    ('VARIABLE', r'[A-Za-z]\w*'),
    ('PLUSEQ', r'\+='), ('MINUSEQ', r'-='), ('MULEQ', r'\*='),
    ('DIVEQ', r'/='), ('POWEQ', r'\^='), ('MODEQ', r'%='),
    ('LSHIFT', r'<<'), ('RSHIFT', r'>>'),
    ('GTE', r'>='), ('LTE', r'<='), ('NEQ', r'!='), ('EQEQ', r'=='),
    ('ANDSYM', r'&&'), ('ORSYM', r'\|\|'),
    ('GT', r'>'),('LT', r'<'),('NOTSYM', r'!'),
    ('BITAND', r'&'), ('BITOR', r'\|'), ('BITNOT', r'~'),
    ('EQUAL', r'='), ('ADD', r'\+'),('SUB', r'-'),
    ('MUL', r'\*'),('DIV', r'/'),('MOD', r'%'),('POW', r'\^'),
    ('COMMA', r','), ('DOT', r'\.'), ('COLON', r':'),
    ('LPAREN', r'\('), ('RPAREN', r'\)'),
    ('LBRACE', r'\{'), ('RBRACE', r'\}'),
    ('LBRACK', r'\['), ('RBRACK', r'\]'),
]

KEYWORDS =('give','out','print','say','tell','if','else','elif','while','for','repeat','read','take','push','pop','is','array','switch','case','default','break','continue','pass','return')
FUNCS = ('sqrt','pow','quad1','quad2','len')

def Lexer(code):
    pos=0; toks=[]
    while pos < len(code):
        for name,pat in LEXER_SPEC:
            m=re.match(pat, code[pos:])
            if m:
                t=m.group(0)
                if name!='SKIP':
                    if name=='VARIABLE':
                        low=t.lower()
                        if low in ('and','or','not','xor'):
                            name='LOGIC'; t=low
                        elif t in KEYWORDS:
                            name='KEYWORD'
                        elif t in FUNCS:
                            name='FUNC'
                    if name in ('ANDSYM','ORSYM','NOTSYM'):
                        name='LOGIC'
                        if t=='&&': t='and'
                        elif t=='||': t='or'
                        elif t=='!': t='not'
                    toks.append((name,t))
                pos+=len(t); break
        else:
            raise SyntaxError(f'Bad char {code[pos]}')
    return toks

memory={}
FUNCTIONS={}
MAIN_BODIES=[]
MERGE_MAINS = True

class BreakLoop(Exception): pass
class ContinueLoop(Exception): pass
class ReturnValue(Exception):
    def __init__(self, v): self.value=v

def interp(s):
    def repl(m):
        inner=m.group(1).strip()
        try: return str(eval_expr(Lexer(inner)))
        except: return str(memory.get(inner, 0))
    return re.sub(r'\[([^\]]+)\]', repl, s)

def exec_input_tokens(toks_nodot):
    var_name=None; prompt=""
    for t in toks_nodot[1:]:
        if t[0]=='VARIABLE' and var_name is None: var_name=t[1]
        if t[0]=='STRING': prompt=interp(t[1][1:-1])
    if not var_name: return 0
    ui=input(prompt+" " if prompt else f"{var_name}: ")
    try:
        if ui.startswith('[') and ui.endswith(']'):
            memory[var_name]=[int(x.strip()) if x.strip().lstrip('-').isdigit() else float(x.strip()) for x in ui[1:-1].split(',') if x.strip()]
        elif '.' in ui: memory[var_name]=float(ui)
        else: memory[var_name]=int(ui)
    except: memory[var_name]=ui
    return memory[var_name]

# FIXED: comma = new line ONLY if outside () [] {} and outside "string"
def get_stmts(body):
    out=[]; cur=""; depth=0; in_str=False
    for ch in body:
        if ch=='"': in_str=not in_str
        if not in_str:
            if ch in '([{': depth+=1
            elif ch in ')]}': depth-=1
            if (ch==',' or ch=='\n') and depth==0:
                p=cur.strip()
                if p.endswith('.'): p=p[:-1]
                if p.endswith(':'): p=p[:-1]
                if p.strip(): out.append(p.strip())
                cur=""; continue
        cur+=ch
    p=cur.strip()
    if p.endswith('.'): p=p[:-1]
    if p.endswith(':'): p=p[:-1]
    if p.strip(): out.append(p.strip())
    merged=[]
    for st in out:
        if st.startswith('else') and merged and merged[-1].lstrip().startswith('if'):
            merged[-1] = merged[-1] + " else: " + st.split(':',1)[1].strip() if ':' in st else merged[-1]
        else: merged.append(st)
    return merged

def run_function(name, arg_vals):
    if name not in FUNCTIONS: raise NameError(f"No func {name}")
    params, body = FUNCTIONS[name]
    outer = memory.copy()
    for i,p in enumerate(params):
        memory[p] = arg_vals[i] if i < len(arg_vals) else 0
    try:
        for s in get_stmts(body):
            run_action(s)
        ret=0
    except ReturnValue as rv:
        ret=rv.value
    finally:
        for p in params:
            if p in outer: memory[p]=outer[p]
            else: memory.pop(p,None)
    return ret

def eval_expr(toks):
    if not toks: return 0
    clean=[t for t in toks if t[0] not in ('DOT','LBRACE','RBRACE','COLON')]
    no_comma=[t for t in clean if t[0]!='COMMA']
    toks_nodot=[t for t in toks if t[0]!='DOT']
    if toks_nodot and toks_nodot[0][0]=='KEYWORD' and toks_nodot[0][1] in ('read','take'):
        return exec_input_tokens(toks_nodot)
    if not no_comma: return 0
    if no_comma[0][0]=='LBRACK' and no_comma[-1][0]=='RBRACK':
        inner=[]; cur=[]; depth=0
        for tk in clean:
            if tk[0]=='LBRACK':
                if depth==0 and not cur: depth+=1; continue
                depth+=1; cur.append(tk)
            elif tk[0]=='RBRACK':
                depth-=1
                if depth==0:
                    if cur: inner.append(cur); break
                else: cur.append(tk)
            elif tk[0]=='COMMA' and depth==1:
                if cur: inner.append(cur); cur=[]
            else:
                if depth>=1: cur.append(tk)
        if not inner: return []
        return [eval_expr(p) for p in inner]
    # FIXED: Use clean (WITH commas) for FUNC, so pow(2,3) works
    toks=clean
    if toks and toks[0][0]=='FUNC':
        fname=toks[0][1]
        args_toks=[]; cur=[]; d=0
        for t in toks[1:]:
            if t[0]=='LPAREN': d+=1; cur.append(t)
            elif t[0]=='RPAREN': d-=1; cur.append(t)
            elif t[0]=='COMMA' and d==1:
                args_toks.append(cur); cur=[]
            else: cur.append(t)
        if cur: args_toks.append(cur)
        # strip outer parens from each arg
        cleaned_args=[]
        for a in args_toks:
            if a and a[0][0]=='LPAREN' and a[-1][0]=='RPAREN':
                cleaned_args.append(a[1:-1])
            else: cleaned_args.append(a)
        # if call was like sqrt(16) without outer handling, first arg still has parens - eval_expr handles it
        # Actually for sqrt(16): args_toks = [[ (, 16, ) ]] -> cleaned = [[16]]
        # For pow(2,3): args = [[(,2],[3,)] ] -> need smarter: flatten
        # Simpler: re-parse by joining tokens and splitting at top-level commas
        # Rebuild evaled from cleaned_args, handling the split above
        # Fix for pow case: first arg has '(' prefix, last has ')' suffix
        # So we reconstruct: if len(cleaned_args)==2 and cleaned_args[0] and cleaned_args[0][0][0]=='LPAREN':
        # we already stripped, it's ok. Evaluate:
        evaled=[]
        for a in cleaned_args:
            if a: evaled.append(eval_expr(a))
        if fname=='len':
            a=evaled[0] if evaled else 0
            return len(a) if isinstance(a,(list,str)) else 0
        if fname=='sqrt' and evaled: return py_math.sqrt(evaled[0])
        if fname=='pow' and len(evaled)>=2: return evaled[0]**evaled[1]
        if fname=='quad1' and len(evaled)>=3: a,b,c=evaled[:3]; return (-b+py_math.sqrt(b*b-4*a*c))/(2*a)
        if fname=='quad2' and len(evaled)>=3: a,b,c=evaled[:3]; return (-b-py_math.sqrt(b*b-4*a*c))/(2*a)
        return 0

    toks=no_comma
    def parse_atom(j):
        if j>=len(toks): return 0,j
        if toks[j][0]=='BITNOT':
            v,nj=parse_atom(j+1); return ~int(v), nj
        t=toks[j]
        if t[0]=='INT': return int(t[1]), j+1
        if t[0]=='FLOAT': return float(t[1]), j+1
        if t[0]=='STRING': return interp(t[1][1:-1]), j+1
        if t[0]=='VARIABLE':
            if j+1 < len(toks) and toks[j+1][0]=='LPAREN':
                k=j+2; d=1; arg_toks=[]; cur=[]
                while k < len(toks):
                    if toks[k][0]=='LPAREN': d+=1; cur.append(toks[k])
                    elif toks[k][0]=='RPAREN':
                        d-=1
                        if d==0:
                            if cur: arg_toks.append(cur)
                            break
                        cur.append(toks[k])
                    elif toks[k][0]=='COMMA' and d==1:
                        arg_toks.append(cur); cur=[]
                    else:
                        cur.append(toks[k])
                    k+=1
                evaled_args=[eval_expr(a) for a in arg_toks]
                if t[1] in FUNCTIONS:
                    return run_function(t[1], evaled_args), k+1
            if j+1 < len(toks) and toks[j+1][0]=='LBRACK':
                k=j+2; d=1; idx_t=[]
                while k < len(toks):
                    if toks[k][0]=='LBRACK': d+=1
                    elif toks[k][0]=='RBRACK':
                        d-=1
                        if d==0: break
                    idx_t.append(toks[k]); k+=1
                idx=int(eval_expr(idx_t)) if idx_t else 0
                arr=memory.get(t[1], [])
                if isinstance(arr,list) and 0 <= idx < len(arr): return arr[idx], k+1
                return 0, k+1
            return memory.get(t[1],0), j+1
        if t[0]=='LPAREN':
            k=j+1; inner=[]; d=1
            while k < len(toks):
                if toks[k][0]=='LPAREN': d+=1
                elif toks[k][0]=='RPAREN':
                    d-=1
                    if d==0: break
                inner.append(toks[k]); k+=1
            return eval_expr(inner), k+1
        return 0,j+1

    def parse_pow(j):
        v,j=parse_atom(j)
        if j<len(toks) and toks[j][0]=='POW': rv,j=parse_pow(j+1); return v**rv, j
        return v,j
    def parse_mul(j):
        v,j=parse_pow(j)
        while j<len(toks) and toks[j][0] in ('MUL','DIV','MOD'):
            op=toks[j][0]; rv,j=parse_pow(j+1)
            if op=='MUL': v=v*rv
            elif op=='DIV': v=v/rv if rv!=0 else 0
            else: v=v%rv if rv!=0 else 0
        return v,j
    def parse_add(j):
        v,j=parse_mul(j)
        while j<len(toks) and toks[j][0] in ('ADD','SUB'):
            op=toks[j][0]; rv,j=parse_mul(j+1)
            v=v+rv if op=='ADD' else v-rv
        return v,j
    def parse_shift(j):
        v,j=parse_add(j)
        while j<len(toks) and toks[j][0] in ('LSHIFT','RSHIFT'):
            op=toks[j][0]; rv,j=parse_add(j+1)
            v= int(v) << int(rv) if op=='LSHIFT' else int(v) >> int(rv)
        return v,j
    def parse_bitand(j):
        v,j=parse_shift(j)
        while j<len(toks) and toks[j][0]=='BITAND':
            rv,j=parse_shift(j+1); v=int(v) & int(rv)
        return v,j
    def parse_bitxor(j):
        v,j=parse_bitand(j)
        while j<len(toks) and toks[j][0]=='LOGIC' and toks[j][1]=='xor':
            rv,j=parse_bitand(j+1); v=int(v) ^ int(rv)
        return v,j
    def parse_bitor(j):
        v,j=parse_bitxor(j)
        while j<len(toks) and toks[j][0]=='BITOR':
            rv,j=parse_bitxor(j+1); v=int(v) | int(rv)
        return v,j
    def parse_cmp(j):
        v,j=parse_bitor(j)
        while j<len(toks) and toks[j][0] in ('GTE','LTE','NEQ','EQEQ','GT','LT'):
            op=toks[j][0]; rv,j=parse_bitor(j+1)
            if op=='GT': v=1 if v>rv else 0
            elif op=='LT': v=1 if v<rv else 0
            elif op=='EQEQ': v=1 if v==rv else 0
            elif op=='NEQ': v=1 if v!=rv else 0
            elif op=='GTE': v=1 if v>=rv else 0
            else: v=1 if v<=rv else 0
        return v,j
    def parse_not(j):
        if j<len(toks) and toks[j][0]=='LOGIC' and toks[j][1]=='not':
            v,j=parse_not(j+1); return 0 if v else 1, j
        return parse_cmp(j)
    def parse_and(j):
        v,j=parse_not(j)
        while j<len(toks) and toks[j][0]=='LOGIC' and toks[j][1]=='and':
            rv,j=parse_not(j+1); v=1 if (v and rv) else 0
        return v,j
    def parse_or(j):
        v,j=parse_and(j)
        while j<len(toks) and toks[j][0]=='LOGIC' and toks[j][1]=='or':
            rv,j=parse_and(j+1); v=1 if (v or rv) else 0
        return v,j
    v,_=parse_or(0); return v

def run_action(code):
    code=code.strip()
    if not code or code=="pass": return
    if code=="break": raise BreakLoop()
    if code=="continue": raise ContinueLoop()
    if code.lower().startswith("return"):
        toks=Lexer(code)
        if len(toks)>1:
            val=eval_expr(toks[1:])
        else: val=0
        raise ReturnValue(val)
    if code.startswith(('if','while','for','repeat','switch')):
        run_block(code if code.endswith('.') else code+'.'); return
    toks=Lexer(code)
    if not toks: return
    if len(toks)==4 and toks[0][0]=='VARIABLE' and toks[1][0]=='LBRACK' and toks[2][0]=='INT' and toks[3][0]=='RBRACK':
        memory[toks[0][1]]=[0]*int(toks[2][1]); return
    if len(toks)>=5 and toks[0][0]=='VARIABLE':
        if toks[1][0]=='EQUAL' and toks[2][0]=='KEYWORD' and toks[2][1]=='array' and toks[3][0]=='LBRACK' and toks[4][0]=='INT':
            memory[toks[0][1]]=[0]*int(toks[4][1]); return
        if len(toks)>=6 and toks[1][0]=='KEYWORD' and toks[1][1]=='is' and toks[2][0]=='KEYWORD' and toks[2][1]=='array' and toks[3][0]=='LBRACK' and toks[4][0]=='INT':
            memory[toks[0][1]]=[0]*int(toks[4][1]); return
    # FIXED: x = read "prompt"
    if len(toks)>=3 and toks[0][0]=='VARIABLE' and toks[1][0]=='EQUAL' and toks[2][0]=='KEYWORD' and toks[2][1] in ('read','take'):
        memory[toks[0][1]]=exec_input_tokens(toks[2:]); return
    if len(toks)>=3 and toks[0][0]=='VARIABLE' and toks[1][0]=='EQUAL' and toks[2][0]=='LBRACK':
        memory[toks[0][1]]=eval_expr(toks[2:]); return
    if len(toks)>=4 and toks[0][0]=='VARIABLE' and toks[1][0]=='KEYWORD' and toks[1][1]=='is' and toks[2][0]=='LBRACK':
        memory[toks[0][1]]=eval_expr(toks[2:]); return
    if toks[0][0]=='KEYWORD' and toks[0][1]=='push':
        if len(toks)>=2 and toks[1][0]=='VARIABLE':
            arr_name=toks[1][1]
            val=eval_expr([t for t in toks[2:] if t[0] not in ('COMMA','COLON')])
            if arr_name in memory and isinstance(memory[arr_name], list): memory[arr_name].append(val)
            else: memory[arr_name]=[val]
        return
    if toks[0][0]=='KEYWORD' and toks[0][1]=='pop':
        if len(toks)>=2 and toks[1][0]=='VARIABLE':
            a=memory.get(toks[1][1],[])
            if isinstance(a,list) and a: print(a.pop())
        return
    if toks[0][0]=='KEYWORD' and toks[0][1] in ('read','take'):
        var_name=None; prompt=""
        for t in toks[1:]:
            if t[0]=='VARIABLE' and var_name is None: var_name=t[1]
            if t[0]=='STRING': prompt=interp(t[1][1:-1])
        if var_name:
            ui=input(prompt+" " if prompt else f"{var_name}: ")
            try:
                if ui.startswith('[') and ui.endswith(']'):
                    memory[var_name]=[int(x.strip()) if x.strip().lstrip('-').isdigit() else float(x.strip()) for x in ui[1:-1].split(',') if x.strip()]
                elif '.' in ui: memory[var_name]=float(ui)
                else: memory[var_name]=int(ui)
            except: memory[var_name]=ui
        return
    if toks[0][0]=='KEYWORD' and toks[0][1] in ('give','out','print','say','tell'):
        for t in toks:
            if t[0]=='STRING': print(interp(t[1][1:-1])); return
        if len(toks)>1: print(eval_expr(toks[1:])); return
        return
    if len(toks)>=4 and toks[0][0]=='VARIABLE' and toks[1][0]=='LBRACK':
        k=2; idx_t=[]
        while k < len(toks) and toks[k][0]!='RBRACK': idx_t.append(toks[k]); k+=1
        if k < len(toks) and toks[k][0]=='RBRACK' and k+1 < len(toks) and toks[k+1][0] in ('EQUAL','PLUSEQ','MINUSEQ','MULEQ','DIVEQ','POWEQ','MODEQ'):
            var=toks[0][1]; idx=int(eval_expr(idx_t)); op=toks[k+1][0]
            rhs=eval_expr(toks[k+2:]) if k+2 < len(toks) else 0
            if var not in memory or not isinstance(memory[var], list): memory[var]=[]
            while len(memory[var]) <= idx: memory[var].append(0)
            if op=='EQUAL': memory[var][idx]=rhs
            elif op=='PLUSEQ': memory[var][idx]+=rhs
            elif op=='MINUSEQ': memory[var][idx]-=rhs
            elif op=='MULEQ': memory[var][idx]*=rhs
            elif op=='DIVEQ': memory[var][idx]/=rhs if rhs!=0 else 0
            elif op=='POWEQ': memory[var][idx]**=rhs
            else: memory[var][idx]%=rhs if rhs!=0 else 0
            return
    if len(toks)>=2 and toks[0][0]=='VARIABLE' and toks[1][0] in ('EQUAL','PLUSEQ','MINUSEQ','MULEQ','DIVEQ','POWEQ','MODEQ'):
        var=toks[0][1]; op=toks[1][0]
        if len(toks)>=3 and toks[2][0]=='STRING' and op=='EQUAL': memory[var]=interp(toks[2][1][1:-1]); return
        rhs_toks = toks[2:]
        rhs=eval_expr(rhs_toks) if len(toks)>2 else 0
        if op=='EQUAL': memory[var]=rhs
        else:
            cur=memory.get(var,0)
            if op=='PLUSEQ': memory[var]=cur+rhs
            elif op=='MINUSEQ': memory[var]=cur-rhs
            elif op=='MULEQ': memory[var]=cur*rhs
            elif op=='DIVEQ': memory[var]=cur/rhs if rhs!=0 else 0
            elif op=='POWEQ': memory[var]=cur**rhs
            else: memory[var]=cur%rhs if rhs!=0 else 0
        return
    if len(toks)>=3 and toks[0][0]=='VARIABLE' and toks[1][0]=='LPAREN' and toks[0][1] in FUNCTIONS:
        eval_expr(toks)
        return

def run_block(b):
    b=b.strip()
    if not b: return
    if b.endswith('='): print(eval_expr(Lexer(b[:-1]))); return
    if not b.endswith('.'):
        if '}' in b: b=b+'.'
        else: raise SyntaxError('Need DOT.')
    raw=b[:-1].strip()
    m=re.match(r'^(F|Func|func)\s+([A-Za-z]\w*)\s*(?:\((.*?)\))?\s*:\s*(.*)$', raw, re.DOTALL)
    if m:
        _, fname, param_str, rest = m.groups()
        rest=rest.strip()
        if rest.startswith('{') and rest.endswith('}'):
            body=rest[1:-1]
        else:
            body=rest
        params=[p.strip() for p in param_str.split(',') if p.strip()] if param_str else []
        if fname.lower() == 'main':
            if MAIN_BODIES and not MERGE_MAINS:
                raise SyntaxError("Two main cannot coexist")
            MAIN_BODIES.append(body)
            FUNCTIONS['main'] = ([], " , ".join(MAIN_BODIES))
            print(f"[defined main {len(MAIN_BODIES)}]")
        else:
            FUNCTIONS[fname]= (params, body)
            print(f"[defined func {fname}({','.join(params)})]")
        return
    b=raw
    if b.startswith('switch'):
        m=re.match(r'switch\s+(.+?):\s*\{(.*)\}\s*$', b, re.DOTALL)
        if not m: raise SyntaxError('switch syntax')
        switch_val = eval_expr(Lexer(m.group(1)))
        body=m.group(2)
        cases = re.findall(r'case\s+(.+?):\s*\{(.*?)\}', body, re.DOTALL)
        default_m = re.search(r'default\s*:\s*\{(.*)\}', body, re.DOTALL)
        matched=False
        for c_expr, c_block in cases:
            if eval_expr(Lexer(c_expr)) == switch_val:
                for s in get_stmts(c_block): run_action(s)
                matched=True; break
        if not matched and default_m:
            for s in get_stmts(default_m.group(1)): run_action(s)
        return
    if b.startswith('if'):
        m=re.match(r'if\s+(.+?):\s*\{(.*)\}\s*else\s*:\s*\{(.*)\}\s*$', b, re.DOTALL)
        if m:
            cond,tb,fb=m.groups()
            if eval_expr(Lexer(cond)):
                for s in get_stmts(tb): run_action(s)
            else:
                for s in get_stmts(fb): run_action(s)
            return
        m=re.match(r'if\s+(.+?):\s*\{(.*)\}\s*else\s*:\s*(.+)\s*$', b, re.DOTALL)
        if m:
            cond,tb,fb=m.groups()
            if eval_expr(Lexer(cond)):
                for s in get_stmts(tb): run_action(s)
            else: run_action(fb)
            return
        m=re.match(r'if\s+(.+?):\s*\{(.*)\}\s*$', b, re.DOTALL)
        if m:
            cond,tb=m.groups()
            if eval_expr(Lexer(cond)):
                for s in get_stmts(tb): run_action(s)
            return
        m=re.match(r'if\s+(.+?):\s*(.+?)\s+else\s*:\s*(.+)\s*$', b, re.DOTALL)
        if m:
            cond,t,f=m.groups()
            run_action(t if eval_expr(Lexer(cond)) else f)
            return
        m=re.match(r'if\s+(.+?):\s*(.+)\s*$', b, re.DOTALL)
        if m:
            cond,t=m.groups()
            if eval_expr(Lexer(cond)): run_action(t)
            return
        raise SyntaxError('if syntax')
    if b.startswith('while'):
        m=re.match(r'while\s+(.+?):\s*\{(.*)\}\s*$', b, re.DOTALL)
        if m:
            cond,body=m.groups()
            while eval_expr(Lexer(cond)):
                try:
                    for s in get_stmts(body): run_action(s)
                except ContinueLoop: continue
                except BreakLoop: break
            return
        m=re.match(r'while\s+(.+?):\s*(.+)\s*$', b, re.DOTALL)
        if m:
            cond,single=m.groups()
            while eval_expr(Lexer(cond)):
                try: run_action(single)
                except ContinueLoop: continue
                except BreakLoop: break
            return
    if b.startswith('for'):
        m=re.match(r'for\s+(.+?),\s*(.+?),\s*(.+?):\s*\{(.*)\}\s*$', b, re.DOTALL)
        if m:
            init,cond,step,body=m.groups()
            run_action(init)
            while eval_expr(Lexer(cond)):
                try:
                    for s in get_stmts(body): run_action(s)
                except ContinueLoop: pass
                except BreakLoop: break
                run_action(step)
            return
        m=re.match(r'for\s+(.+?),\s*(.+?),\s*(.+?):\s*(.+)\s*$', b, re.DOTALL)
        if m:
            init,cond,step,single=m.groups()
            run_action(init)
            while eval_expr(Lexer(cond)):
                try: run_action(single)
                except ContinueLoop: pass
                except BreakLoop: break
                run_action(step)
            return
    if b.startswith('repeat'):
        m=re.match(r'repeat\s*\(\s*(.+?)\s*\)\s*:\s*\{(.*)\}\s*$', b, re.DOTALL)
        if m:
            times=int(eval_expr(Lexer(m.group(1))))
            for _ in range(times):
                try:
                    for s in get_stmts(m.group(2)): run_action(s)
                except ContinueLoop: continue
                except BreakLoop: break
            return
        m=re.match(r'repeat\s*\(\s*(.+?)\s*\)\s*:\s*(.+)\s*$', b, re.DOTALL)
        if m:
            times=int(eval_expr(Lexer(m.group(1))))
            for _ in range(times):
                try: run_action(m.group(2))
                except ContinueLoop: continue
                except BreakLoop: break
            return
    run_action(b)

buf=""
print("POP with funcs - F/Func/func, main merges if MERGE_MAINS=True")
print("Type 'run.' to run main if defined")
while True:
    c=input(">> " if not buf else ".. ")
    if c.strip()=="exit": break
    if c.strip()=="run." or c.strip()=="run":
        if MAIN_BODIES:
            try:
                _, merged = FUNCTIONS['main']
                for s in get_stmts(merged): run_action(s)
            except ReturnValue:
                pass
            except Exception as e: print("Error in main:",e)
        else:
            print("No main - top-level code already runs")
        continue
    buf=c if not buf else buf+"\n"+c
    if buf.count('{')>buf.count('}'): continue
    if buf.strip().endswith(','): continue
    if buf.strip().endswith('.') or buf.strip().endswith('='):
        try: run_block(buf)
        except Exception as e: print("Error:",e)
        buf=""
