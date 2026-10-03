"""Helpers compartidos para editar el Word del proyecto sin pasar por Word.

Todo trabaja sobre el XML de `word/document.xml` como texto. Ningún helper toca
`<w:drawing>`, `<w:pict>`, `word/media` ni las relaciones: las imágenes sólo se
mueven como párrafo completo. Ver `../como-editar-el-word.md`.
"""
import re, html, zipfile, hashlib, collections

# ---------------------------------------------------------------------------
# Lectura y escritura del .docx
# ---------------------------------------------------------------------------
def abrir(path):
    """Devuelve el XML de word/document.xml como str."""
    with zipfile.ZipFile(path) as z:
        return z.read('word/document.xml').decode('utf8')

def guardar(original, xml, salida):
    """Copia cada entrada de `original` tal cual y reemplaza sólo word/document.xml."""
    with zipfile.ZipFile(original) as src, zipfile.ZipFile(salida, 'w', zipfile.ZIP_DEFLATED) as z:
        for info in src.infolist():
            data = xml.encode('utf8') if info.filename == 'word/document.xml' else src.read(info.filename)
            z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)

def dibujos(xml):
    return re.findall(r'<w:drawing>.*?</w:drawing>|<w:pict>.*?</w:pict>', xml, re.S)

def tiene_imagen(s):
    return '<w:drawing' in s or '<w:pict' in s or '<w:object' in s

# ---------------------------------------------------------------------------
# Estructura: elementos de primer nivel, filas, celdas, texto
# ---------------------------------------------------------------------------
def elements(x):
    b0=x.index('<w:body>')+8; b1=x.rindex('</w:body>')
    body=x[b0:b1]
    pat=re.compile(r'<(/?)w:(p|tbl|sdt|sectPr)\b[^>]*?(/?)>')
    depth=0;els=[]
    for m in pat.finditer(body):
        close,name,selfc=m.group(1),m.group(2),m.group(3)
        if selfc:
            if depth==0: els.append((name,b0+m.start(),b0+m.end()))
            continue
        if not close:
            if depth==0: start=m.start();tag=name
            depth+=1
        else:
            depth-=1
            if depth==0: els.append((tag,b0+start,b0+m.end()))
    return els
def txt(s): return ''.join(re.findall(r'<w:t(?:\s[^>]*)?>([^<]*)</w:t>',s))
def rows(tbl):
    return re.findall(r'<w:tr[ >].*?</w:tr>',tbl,flags=re.S)
def cells(tr):
    return re.findall(r'<w:tc>.*?</w:tc>',tr,flags=re.S)

def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def strip_ids(s):
    return re.sub(r'\s(?:w14:paraId|w14:textId)="[^"]*"', '', s)

def _t(text):
    return f'<w:t xml:space="preserve">{esc(text)}</w:t>'

def runs(text, rpr=''):
    """**negrita** dentro del texto -> runs separados."""
    out = []
    parts = re.split(r'(\*\*.+?\*\*)', text)
    for p in parts:
        if not p:
            continue
        if p.startswith('**') and p.endswith('**'):
            inner = rpr.replace('<w:rPr>', '').replace('</w:rPr>', '')
            inner = re.sub(r'<w:b/>|<w:bCs/>', '', inner)
            out.append(f'<w:r><w:rPr>{inner}<w:b/><w:bCs/></w:rPr>{_t(p[2:-2])}</w:r>')
        else:
            out.append(f'<w:r>{rpr}{_t(p)}</w:r>')
    return ''.join(out)

BODY_PPR = '<w:pPr><w:spacing w:line="276" w:lineRule="auto"/></w:pPr>'

def P(text):
    return f'<w:p>{BODY_PPR}{runs(text)}</w:p>'

def EMPTY():
    return f'<w:p>{BODY_PPR}</w:p>'

def H(style, text, ind=None):
    i = f'<w:ind w:left="{ind}"/>' if ind else ''
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/>{i}</w:pPr>{runs(text)}</w:p>'

def BUL(text):
    rpr = '<w:rPr><w:rFonts w:cs="Times New Roman"/><w:color w:val="auto"/></w:rPr>'
    return ('<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="39"/></w:numPr>'
            '<w:spacing w:line="276" w:lineRule="auto"/>' + rpr + '</w:pPr>' + runs(text, rpr) + '</w:p>')

CODE_RPR = ('<w:rPr><w:rFonts w:ascii="Consolas" w:eastAsia="Consolas" w:hAnsi="Consolas" '
            'w:cs="Consolas"/><w:color w:val="{c}"/><w:sz w:val="21"/><w:szCs w:val="21"/>'
            '<w:lang w:val="en-US"/></w:rPr>')

def CODE(line):
    ppr = ('<w:pPr><w:shd w:val="clear" w:color="auto" w:fill="121314"/>'
           '<w:spacing w:line="285" w:lineRule="auto"/><w:rPr><w:lang w:val="en-US"/></w:rPr></w:pPr>')
    if not line.strip():
        return f'<w:p>{ppr}</w:p>'
    color = '8B949E' if line.lstrip().startswith('--') else 'BBBEBF'
    return f'<w:p>{ppr}<w:r>{CODE_RPR.format(c=color)}{_t(line)}</w:r></w:p>'

# ---------- tablas ----------
PARA_RE = re.compile(r'<w:p(?=[ >]).*?</w:p>', re.S)

def set_cell(tc, text):
    paras = PARA_RE.findall(tc)
    first = paras[0] if paras else '<w:p></w:p>'
    m = re.search(r'<w:pPr>.*?</w:pPr>', first, re.S)
    ppr = m.group(0) if m else ''
    m = re.search(r'<w:r>(<w:rPr>.*?</w:rPr>)', first, re.S) or \
        re.search(r'<w:r [^>]*>(<w:rPr>.*?</w:rPr>)', first, re.S)
    if m:
        rpr = m.group(1)
    else:
        m2 = re.search(r'<w:pPr>.*?(<w:rPr>.*?</w:rPr>).*?</w:pPr>', first, re.S)
        rpr = m2.group(1) if m2 else ''
    new = ''.join(f'<w:p>{ppr}{runs(line, rpr) if line else ""}</w:p>'
                  for line in text.split('\n'))
    # quitar todos los párrafos y poner el nuevo donde estaba el primero
    start = tc.find(first) if paras else tc.rfind('</w:tc>')
    body = PARA_RE.sub('', tc)
    tcpr_end = body.find('</w:tcPr>')
    pos = tcpr_end + len('</w:tcPr>') if tcpr_end >= 0 else len('<w:tc>')
    return body[:pos] + new + body[pos:]

def set_row(tr, texts):
    cs = cells(tr)
    out = tr
    for c, t in zip(cs, texts):
        if t is None:
            continue
        out = out.replace(c, set_cell(c, t), 1)
    return strip_ids(out)

def split_tbl(tbl):
    rs = rows(tbl)
    a = tbl.find(rs[0])
    z = tbl.rfind(rs[-1]) + len(rs[-1])
    return tbl[:a], rs, tbl[z:]

def table(tbl, keep, data, tpl_row):
    """keep: lista de (índice de fila, textos|None) que se conservan en ese orden;
    data: filas nuevas clonadas de la fila tpl_row."""
    pre, rs, post = split_tbl(tbl)
    out = []
    for i, texts in keep:
        out.append(rs[i] if texts is None else set_row(rs[i], texts))
    for d in data:
        out.append(set_row(rs[tpl_row], d))
    return strip_ids(pre + ''.join(out) + post)

PAGE_W = 8828   # ancho de tabla normal (texto útil = 12240-2*1701 = 8838)
DAILY_W, DAILY_IND = 10405, -714
DAILY_GRID9 = [1481, 1052, 1232, 1155, 1172, 1114, 1202, 1074, 923]
HDR_TEST, BAND_TEST = '17324D', 'F2F6F9'
TEST_MAR = ('<w:tcMar><w:top w:w="90" w:type="dxa"/><w:left w:w="110" w:type="dxa"/>'
            '<w:bottom w:w="90" w:type="dxa"/><w:right w:w="110" w:type="dxa"/></w:tcMar>')
# párrafo vacío autocerrado primero: si no, <w:p .../> se tragaría hasta el próximo </w:p>
PARA_RE = re.compile(r'<w:p(?:\s[^>]*?)?/>|<w:p(?:\s[^>]*)?>.*?</w:p>', re.S)

def scale(grid, total):
    s = sum(grid)
    out = [round(g * total / s) for g in grid]
    out[-1] += total - sum(out)
    return out

def get_grid(tbl):
    return [int(g) for g in re.findall(r'<w:gridCol w:w="(\d+)"', tbl[:tbl.find('<w:tr')])]

def set_widths(tbl, grid, tblw=None, ind=None):
    """Reescribe tblGrid, tblW, tblInd y cada tcW según la grilla."""
    head_end = tbl.find('<w:tr')
    head, body = tbl[:head_end], tbl[head_end:]
    head = re.sub(r'<w:tblGrid>.*?</w:tblGrid>',
                  '<w:tblGrid>' + ''.join(f'<w:gridCol w:w="{g}"/>' for g in grid) + '</w:tblGrid>',
                  head, flags=re.S)
    if tblw is not None:
        head = re.sub(r'<w:tblW [^>]*/>', f'<w:tblW w:w="{tblw}" w:type="dxa"/>', head, 1)
    head = re.sub(r'<w:tblInd [^>]*/>', '', head)
    if ind is not None:
        head = head.replace('<w:tblLayout', f'<w:tblInd w:w="{ind}" w:type="dxa"/><w:tblLayout', 1) \
            if '<w:tblLayout' in head else re.sub(r'(<w:tblW [^>]*/>)', rf'\1<w:tblInd w:w="{ind}" w:type="dxa"/>', head, 1)
    def fix_row(tr):
        m = re.search(r'<w:gridBefore w:val="(\d+)"/>', tr)
        col = int(m.group(1)) if m else 0
        out, pos = [], 0
        for tc in cells(tr):
            i = tr.find(tc, pos)
            out.append(tr[pos:i])
            sp = re.search(r'<w:gridSpan w:val="(\d+)"/>', tc)
            span = int(sp.group(1)) if sp else 1
            w = sum(grid[col:col + span])
            col += span
            if '<w:tcW ' in tc:
                tc2 = re.sub(r'<w:tcW [^>]*/>', f'<w:tcW w:w="{w}" w:type="dxa"/>', tc, 1)
            elif '<w:tcPr>' in tc:
                tc2 = tc.replace('<w:tcPr>', f'<w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>', 1)
            else:
                tc2 = tc.replace('<w:tc>', f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/></w:tcPr>', 1)
            out.append(tc2)
            pos = i + len(tc)
        out.append(tr[pos:])
        return ''.join(out)
    for tr in rows(body):
        body = body.replace(tr, fix_row(tr), 1)
    return head + body

_SHD = re.compile(r'<w:shd [^>]*/>')
_AFTER_SHD = ['<w:noWrap', '<w:tcMar', '<w:textDirection', '<w:tcFitText', '<w:vAlign', '<w:hideMark', '</w:tcPr>']
_AFTER_MAR = ['<w:textDirection', '<w:tcFitText', '<w:vAlign', '<w:hideMark', '</w:tcPr>']

def _tcpr(tc):
    if '<w:tcPr>' not in tc:
        tc = tc.replace('<w:tc>', '<w:tc><w:tcPr></w:tcPr>', 1)
    return tc, re.search(r'<w:tcPr>.*?</w:tcPr>', tc, re.S).group(0)

def _insert(pr, piece, before):
    for k in before:
        if k in pr:
            return pr.replace(k, piece + k, 1)
    return pr

def set_fill(tc, fill):
    """Sombreado de la celda (sólo en tcPr; no toca el contenido)."""
    tc, pr = _tcpr(tc)
    pr2 = _SHD.sub('', pr)
    if fill:
        pr2 = _insert(pr2, f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>', _AFTER_SHD)
    return tc.replace(pr, pr2, 1)

def set_mar(tc, mar):
    tc, pr = _tcpr(tc)
    pr2 = _insert(re.sub(r'<w:tcMar>.*?</w:tcMar>', '', pr, flags=re.S), mar, _AFTER_MAR)
    return tc.replace(pr, pr2, 1)

def test_style(tbl):
    """Tablas de pruebas: encabezado 17324D, banda F2F6F9 en filas pares, márgenes 90/110."""
    for i, tr in enumerate(rows(tbl)):
        new = tr
        for tc in cells(tr):
            tc2 = set_fill(tc, HDR_TEST if i == 0 else (BAND_TEST if i % 2 == 0 else None))
            new = new.replace(tc, set_mar(tc2, TEST_MAR), 1)
        tbl = tbl.replace(tr, new, 1)
    return tbl

# ---------- historias de usuario (modelo: US-01 del Sprint 0) ----------
BASE = '<w:rFonts w:cs="Times New Roman"/><w:color w:val="auto"/><w:lang w:eastAsia="es-BO"/>'
BOLD = '<w:rFonts w:cs="Times New Roman"/><w:b/><w:bCs/><w:color w:val="auto"/><w:lang w:eastAsia="es-BO"/>'
PPR = f'<w:pPr><w:ind w:firstLine="0"/><w:rPr>{BASE}</w:rPr></w:pPr>'
PPR_C = f'<w:pPr><w:ind w:firstLine="0"/><w:jc w:val="center"/><w:rPr>{BOLD}</w:rPr></w:pPr>'
TITLE_PPR = '<w:pPr><w:ind w:left="360" w:firstLine="0"/><w:rPr><w:b/><w:bCs/><w:lang w:eastAsia="es-BO"/></w:rPr></w:pPr>'
TITLE_RPR = '<w:rPr><w:b/><w:bCs/><w:lang w:eastAsia="es-BO"/></w:rPr>'

def r(t, bold=False):
    return f'<w:r><w:rPr>{BOLD if bold else BASE}</w:rPr><w:t xml:space="preserve">{esc(t)}</w:t></w:r>'

def p(*runs, ppr=PPR):
    return f'<w:p>{ppr}{"".join(runs)}</w:p>'

def title_par(text):
    text = re.sub(r'^US-(\d)(?=\D)', r'US-0\1', html.unescape(text).strip())
    return f'<w:p>{TITLE_PPR}<w:r>{TITLE_RPR}<w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>'

def empty_par():
    return f'<w:p>{PPR}</w:p>'

def _fill(tr, cell_paras):
    out = tr
    for tc, paras in zip(cells(tr), cell_paras):
        m = re.search(r'<w:tcPr>.*?</w:tcPr>', tc, re.S)
        out = out.replace(tc, '<w:tc>' + (m.group(0) if m else '') + ''.join(paras) + '</w:tc>', 1)
    return out

def inciso(f):
    m = re.match(r'^([a-z]\))\s*(.*)$', f, re.S)
    return p(r(m.group(1), True), r(' ' + m.group(2))) if m else p(r(f))

def story_table(tpl, d):
    """d: short, cu, desc(list), prio, horas, func(list), resp(list de líneas), proto(list)."""
    pre = tpl[:tpl.find('<w:tr ')] if '<w:tr ' in tpl else tpl[:tpl.find('<w:tr>')]
    TR = rows(tpl)
    post = tpl[tpl.rfind('</w:tr>') + len('</w:tr>'):]
    cu_m = re.match(r'^(CU\d+\s*[—-]\s*)(.*)$', d['cu'], re.S)
    cu_runs = [r(cu_m.group(1), True), r(cu_m.group(2))] if cu_m else [r(d['cu'])]
    horas = re.sub(r'^Cant(idad)? Horas\s*:\s*', 'Cant Horas : ', d['horas'])
    resp = []
    for line in d['resp']:
        for part in line.split(' · '):
            if part.strip():
                resp.append(p(r(part.strip())))
    rows_xml = [
        _fill(TR[0], [[p(r(d['short'], True), ppr=PPR_C)]]),
        _fill(TR[1], [[p(*cu_runs)], [p(r(t)) for t in d['desc']] + [p()]]),
        TR[2],
        _fill(TR[3], [[p(r(d['prio']))], [p(r(horas))]]),
        _fill(TR[4], [[p(r('Funcionalidades:'))] + [inciso(f) for f in d['func']]]),
        _fill(TR[5], [[p(r('Responsables: '))] + resp]),
        _fill(TR[6], [[p(r(t)) for t in d['proto']] + [p(), p()]]),
    ]
    return strip_ids(pre + ''.join(rows_xml) + post)

def parse_story(tbl):
    rs = rows(tbl)
    def ps(i, j=0):
        return [html.unescape(txt(x)) for x in PARA_RE.findall(cells(rs[i])[j])]
    nz = lambda L: [t.strip() for t in L if t.strip()]
    f = nz(ps(4)); assert f[0] == 'Funcionalidades:', f[:1]
    rp = nz(ps(5)); assert rp[0].startswith('Responsables'), rp[:1]
    return {'short': ' '.join(nz(ps(0))), 'cu': ' '.join(nz(ps(1, 0))), 'desc': nz(ps(1, 1)),
            'prio': ' '.join(nz(ps(3, 0))), 'horas': ' '.join(nz(ps(3, 1))),
            'func': f[1:], 'resp': rp[1:] or [], 'proto': nz(ps(6))}

_IND_BEFORE = ['<w:contextualSpacing', '<w:mirrorIndents', '<w:suppressOverlap', '<w:jc ', '<w:textDirection',
               '<w:textAlignment', '<w:textboxTightWrap', '<w:outlineLvl', '<w:divId', '<w:cnfStyle', '<w:rPr>',
               '<w:sectPr', '<w:pPrChange', '</w:pPr>']

def cell_ind0(xml):
    """Párrafos de celda sin sangría propia -> firstLine 0 (el Normal hereda 284).
    No toca párrafos numerados ni los que ya declaran <w:ind>."""
    def fix(m):
        p = m.group(0)
        if p.endswith('/>') and '</w:p>' not in p:
            return p[:-2] + '><w:pPr><w:ind w:firstLine="0"/></w:pPr></w:p>'
        pm = re.search(r'<w:pPr>.*?</w:pPr>', p, re.S)
        if pm:
            ppr = pm.group(0)
            if '<w:ind ' in ppr or '<w:numPr>' in ppr:
                return p
            for k in _IND_BEFORE:
                if k in ppr:
                    return p.replace(ppr, ppr.replace(k, '<w:ind w:firstLine="0"/>' + k, 1), 1)
        return re.sub(r'^(<w:p(?: [^>]*)?>)', r'\1<w:pPr><w:ind w:firstLine="0"/></w:pPr>', p, 1)
    def per_tbl(t):
        return PARA_RE.sub(fix, t.group(0))
    return re.sub(r'<w:tbl>.*?</w:tbl>', per_tbl, xml, flags=re.S)

def bold_labels(tbl):
    """Cabecera del Sprint Backlog: 'Etiqueta:' en negrita y el valor normal (como Sprint 0/1)."""
    out = tbl
    for tc in cells(tbl):
        if '<w:b/>' in tc:
            continue
        ps = PARA_RE.findall(tc)
        if len(ps) != 1:
            continue
        t = html.unescape(txt(ps[0]))
        m = re.match(r'^([^:]{1,40}:)(.*)$', t, re.S)
        if not m:
            continue
        ppr = re.search(r'<w:pPr>.*?</w:pPr>', ps[0], re.S)
        ppr = ppr.group(0) if ppr else PPR
        newp = f'<w:p>{ppr}{r(m.group(1), True)}{r(m.group(2))}</w:p>'
        out = out.replace(tc, tc.replace(ps[0], newp, 1), 1)
    return out

clone_table = table

# ---------------------------------------------------------------------------
# Anclas por texto (los índices cambian de un documento a otro)
# ---------------------------------------------------------------------------
def buscar(xml, E, texto, estilo=None, desde=0, hasta=None, exacto=True):
    """Índice del primer elemento párrafo cuyo texto (sin espacios de borde) es `texto`."""
    hasta = len(E) if hasta is None else hasta
    for n in range(desde, hasta):
        t, a, b = E[n]
        if t != 'p':
            continue
        s = xml[a:b]
        tx = html.unescape(txt(s)).strip()
        if (tx == texto if exacto else tx.startswith(texto)) and (estilo is None or f'w:val="{estilo}"' in s[:600]):
            return n
    raise SystemExit(f'No encontré el ancla {texto!r} (estilo {estilo}) entre {desde} y {hasta}: '
                     'el documento no tiene la estructura esperada. No se forzó nada.')

def limites_sprints(xml, E):
    """{0: (ini, fin), 1: ..., 2: ...} por los títulos Titulo11 'Sprint N'."""
    s = [buscar(xml, E, f'Sprint {k}', 'Titulo11') for k in range(4)]
    return {k: (s[k], s[k + 1]) for k in range(3)}

def aplicar(xml, E, ops):
    """ops: {índice: xml nuevo ('' borra)}. Se aplica de atrás hacia adelante."""
    out = xml
    for n in sorted(ops, reverse=True):
        t, a, b = E[n]
        out = out[:a] + ops[n] + out[b:]
    return out
