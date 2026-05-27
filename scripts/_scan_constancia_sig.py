import re
import zipfile

path = r'core/pos/templates/frm/ctascollect/constancia_pago.docx'
with zipfile.ZipFile(path) as z:
    doc = z.read('word/document.xml').decode('utf-8', 'ignore')
    rels = z.read('word/_rels/document.xml.rels').decode('utf-8', 'ignore')
    print('rels images:', re.findall(r'Target="media/([^"]+)"', rels))
    for key in ('image3', 'CHANCHA', 'v:shape', 'pict', 'txbx', 'blip'):
        print(key, doc.count(key))
    i = doc.find('rId')
    # find embed for image3
    for m in re.finditer(r'r:embed="(rId\d+)"', doc):
        rid = m.group(1)
        if 'image3' in rels and rid in rels:
            pos = m.start()
            snippet = doc[max(0, pos - 200) : pos + 400]
            if 'image3' in rels[rels.find(rid) : rels.find(rid) + 80]:
                print('image3 embed context:', snippet[:300])
    pos = doc.find('CHANCHA')
    if pos >= 0:
        print('CHANCHA context:', doc[pos - 500 : pos + 600])
