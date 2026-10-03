"""Generadores de XML que reusan el formato del propio documento."""
import re
from lib import *

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
