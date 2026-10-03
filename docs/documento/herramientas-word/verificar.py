"""Comprueba que una edición no tocó las imágenes ni dejó relaciones rotas.

Uso:
    python verificar.py ORIGINAL.docx EDITADO.docx [--validate RUTA/validate.py] [--esperado-dibujos N]

Revisa:
  - que las partes del paquete fuera de word/document.xml sean byte a byte iguales
    (word/media/*, los .rels, styles, numbering, encabezados y pies, ...);
  - que el conjunto de <w:drawing>/<w:pict> sea el mismo (mismo XML, misma cantidad):
    moverlos está permitido, cambiarlos no;
  - que ninguna relación de imagen quede sin uso y que no haya r:embed/r:id sin relación;
  - opcionalmente corre validate.py --original del skill docx.
Sale con código 1 si algo falla.
"""
import argparse, collections, re, subprocess, sys, zipfile, os
from comun import dibujos

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('original'); ap.add_argument('editado')
    ap.add_argument('--validate', help='ruta a scripts/office/validate.py del skill docx')
    ap.add_argument('--permitir-cambio', nargs='*', default=[],
                    help='partes que pueden diferir además de word/document.xml')
    a = ap.parse_args()
    ok = True
    zo, ze = zipfile.ZipFile(a.original), zipfile.ZipFile(a.editado)
    no, ne = set(zo.namelist()), set(ze.namelist())
    if no != ne:
        print('FALLA: partes distintas:', sorted(no ^ ne)); ok = False
    dist = [n for n in sorted(no & ne) if n != 'word/document.xml' and n not in a.permitir_cambio
            and zo.read(n) != ze.read(n)]
    print('partes distintas fuera de document.xml:', dist or 'ninguna')
    ok &= not dist
    do, de = zo.read('word/document.xml').decode('utf8'), ze.read('word/document.xml').decode('utf8')
    Do, De = collections.Counter(dibujos(do)), collections.Counter(dibujos(de))
    print(f'dibujos: {sum(Do.values())} -> {sum(De.values())}; mismo XML: {Do == De}')
    ok &= Do == De
    rels = ze.read('word/_rels/document.xml.rels').decode('utf8')
    ids = {re.search(r'Id="([^"]+)"', m).group(1): m for m in re.findall(r'<Relationship [^>]*>', rels)}
    usados = set(re.findall(r'r:(?:embed|id|link|pict)="(\w+)"', de))
    huerf = [i for i, m in ids.items() if '/image"' in m and i not in usados]
    falt = sorted(usados - set(ids))
    print('relaciones de imagen sin uso:', huerf or 'ninguna', '| referencias sin relación:', falt or 'ninguna')
    ok &= not huerf and not falt
    if a.validate:
        env = dict(os.environ, PYTHONIOENCODING='utf8')
        r = subprocess.run([sys.executable, a.validate, a.editado, '--original', a.original],
                           capture_output=True, text=True, env=env, encoding='utf8')
        print(r.stdout.strip()[-400:]); ok &= 'PASSED' in r.stdout
    print('RESULTADO:', 'OK' if ok else 'FALLA')
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
