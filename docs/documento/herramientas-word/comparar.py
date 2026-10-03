"""Compara dos .docx: qué partes del paquete cambian y qué contenido difiere.

Uso:
    python comparar.py A.docx B.docx [--max 40]

1. Partes del zip con distinto contenido (md5). Si word/media o los .rels difieren,
   las imágenes no son las mismas: no se trasplanta nada entre esos documentos.
2. Diferencias de contenido elemento por elemento (párrafos y tablas de primer nivel),
   comparando texto, cantidad de imágenes y la imagen (por md5 del archivo) que usa cada una.
   Así no cuentan los cambios de marcado que mete Word al guardar (proofErr, rsid,
   runs partidos, rId renumerados).
"""
import argparse, difflib, hashlib, html, re, zipfile
from comun import elements, txt, rows, cells

def partes(p):
    with zipfile.ZipFile(p) as z:
        return {n: hashlib.md5(z.read(n)).hexdigest() for n in z.namelist()}

def items(p):
    with zipfile.ZipFile(p) as z:
        x = z.read('word/document.xml').decode('utf8')
        r = z.read('word/_rels/document.xml.rels').decode('utf8')
        media = {n: hashlib.md5(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('word/media/')}
    rel = {re.search(r'Id="([^"]+)"', m).group(1): re.search(r'Target="([^"]+)"', m).group(1)
           for m in re.findall(r'<Relationship [^>]*>', r)}
    out = []
    for t, a, b in elements(x):
        s = x[a:b]
        if t == 'tbl':
            texto = 'TABLA[' + ' | '.join(' ¦ '.join(html.unescape(txt(c)) for c in cells(f)) for f in rows(s)) + ']'
        else:
            texto = html.unescape(txt(s))
        imgs = tuple(media.get('word/' + rel.get(e, ''), '?')[:8] for e in re.findall(r'r:embed="(\w+)"', s))
        out.append((texto, imgs))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('--max', type=int, default=40)
    a = ap.parse_args()
    pa, pb = partes(a.a), partes(a.b)
    print('== partes del paquete')
    for n in sorted(set(pa) | set(pb)):
        if pa.get(n) != pb.get(n):
            print('  ', n, pa.get(n, '----')[:8], pb.get(n, '----')[:8])
    A, B = items(a.a), items(a.b)
    sm = difflib.SequenceMatcher(None, A, B, autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != 'equal']
    print(f'== contenido: {len(A)} y {len(B)} elementos, {len(ops)} bloques distintos')
    for o, i, j, k, l in ops[:a.max]:
        print(f'{o} A[{i}:{j}] B[{k}:{l}]')
        for s in A[i:j][:3]:
            print('   -', s[0][:160], f'[IMG {len(s[1])}]' if s[1] else '')
        for s in B[k:l][:3]:
            print('   +', s[0][:160], f'[IMG {len(s[1])}]' if s[1] else '')

if __name__ == '__main__':
    main()
