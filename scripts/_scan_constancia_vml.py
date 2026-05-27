import re
import zipfile

path = r'core/pos/templates/frm/ctascollect/constancia_pago.docx'
with zipfile.ZipFile(path) as z:
    doc = z.read('word/document.xml').decode('utf-8', 'ignore')
    rels = z.read('word/_rels/document.xml.rels').decode('utf-8', 'ignore')
    print('rels', rels)
    for m in re.finditer(r'r:embed="(rId\d+)"', doc):
        pos = m.start()
        snip = doc[pos - 300 : pos + 400]
        print('--- embed', m.group(1))
        print(snip[:500])
    for m in re.finditer(r'<v:imagedata[^>]+>', doc):
        print('v:imagedata', m.group(0)[:120])
