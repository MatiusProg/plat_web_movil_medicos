"""Inventario de un .docx: títulos, tablas y formatos, para ubicarse antes de editar.

Uso:
    python inventario.py DOC.docx [--titulos] [--tablas] [--elementos DESDE HASTA] [--formatos DESDE HASTA]

  --titulos            títulos (Titulo*/CAPITULO) con su índice de elemento y si tienen numeración automática
  --tablas             cada tabla: filas x columnas, estilo, ancho, grilla, color de encabezado y primera fila
  --elementos A B      lista los elementos de primer nivel entre A y B (tipo, estilo, [IMG], texto)
  --formatos A B       agrupa los párrafos de texto corrido por formato (pPr + rPr) y cuenta cada uno
Los índices son los de `comun.elements`: cambian de un documento a otro y después de cada edición.
"""
import argparse, collections, html, re
from comun import abrir, elements, txt, rows, cells, get_grid, tiene_imagen

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('docx')
    ap.add_argument('--titulos', action='store_true')
    ap.add_argument('--tablas', action='store_true')
    ap.add_argument('--elementos', nargs=2, type=int)
    ap.add_argument('--formatos', nargs=2, type=int)
    a = ap.parse_args()
    x = abrir(a.docx)
    E = elements(x)
    S = lambda n: x[E[n][1]:E[n][2]]
    T = lambda n: html.unescape(txt(S(n)))
    print('elementos:', len(E))
    if a.titulos:
        for n in range(len(E)):
            s = S(n)
            m = re.search(r'<w:pStyle w:val="([^"]+)"', s[:600])
            if E[n][0] == 'p' and m and re.match(r'(?i)titulo|capitulo', m.group(1)):
                print(n, m.group(1), 'NUM' if '<w:numPr>' in s[:800] else '   ', '|', T(n)[:80])
    if a.tablas:
        for n in range(len(E)):
            if E[n][0] != 'tbl':
                continue
            s = S(n); rs = rows(s)
            st = re.search(r'<w:tblStyle w:val="([^"]+)"', s[:3000])
            tw = re.search(r'<w:tblW w:w="(\d+)" w:type="(\w+)"', s[:3000])
            g = get_grid(s)
            fill = re.findall(r'w:fill="(\w+)"', rs[0])[:1]
            print(n, f'{len(rs)}x{len(g)}', st.group(1) if st else '-', tw.groups() if tw else '-', sum(g), g,
                  'enc', fill, 'IMG' if tiene_imagen(s) else '', '|', html.unescape(txt(rs[0]))[:50])
    if a.elementos:
        for n in range(*a.elementos):
            s = S(n)
            m = re.search(r'<w:pStyle w:val="([^"]+)"', s[:600])
            print(n, E[n][0], m.group(1) if m else '-', '[IMG]' if tiene_imagen(s) else '', '|', T(n)[:120])
    if a.formatos:
        C = collections.Counter(); ej = {}
        for n in range(*a.formatos):
            s = S(n)
            if E[n][0] != 'p' or tiene_imagen(s) or not T(n).strip():
                continue
            m = re.search(r'<w:pPr>(.*?)</w:pPr>', s, re.S)
            ppr = re.sub(r'<w:rPr>.*?</w:rPr>', '', m.group(1) if m else '', flags=re.S)
            if re.search(r'pStyle w:val="(?i:titulo|capitulo)', ppr):
                continue
            rpr = tuple(sorted(set(re.sub(r'<w:lang[^>]*/>|<w:noProof/>', '', r)
                                   for r in re.findall(r'<w:r(?: [^>]*)?>(?:<w:rPr>(.*?)</w:rPr>)?', s, re.S))))[:3]
            C[(ppr, rpr)] += 1; ej.setdefault((ppr, rpr), []).append((n, T(n)[:40]))
        for k, c in C.most_common(30):
            print(c, 'pPr=', k[0][:150]); print('     rPr=', [r[:120] for r in k[1]]); print('     ej:', ej[k][:3])

if __name__ == '__main__':
    main()
