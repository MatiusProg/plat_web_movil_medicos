import re
P='un/word/document.xml'
def load(): return open(P,encoding='utf8').read()
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
