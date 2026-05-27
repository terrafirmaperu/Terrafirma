import re
import zipfile

path = r'core/pos/templates/contracts/CONTRATO SRA. CELIA.docx'
with zipfile.ZipFile(path) as z:
    doc = z.read('word/document.xml').decode('utf-8', 'ignore')
    rels = z.read('word/_rels/document.xml.rels').decode('utf-8', 'ignore')
    rid_map = dict(re.findall(r'Id="(rId\d+)"[^>]*Target="media/([^"]+)"', rels))
    for rid, img in rid_map.items():
        pos = doc.find(f'r:embed="{rid}"')
        if pos < 0:
            continue
        chunk = doc[max(0, pos - 1500) : pos + 200]
        pos_h = re.search(r'wp:posOffset[^>]*>(\d+)</wp:posOffset>', chunk)
        pos_x = re.search(r'<wp:positionH[^>]*>.*?wp:posOffset[^>]*>(\d+)</wp:posOffset>', chunk, re.DOTALL)
        pos_y = re.search(r'<wp:positionV[^>]*>.*?wp:posOffset[^>]*>(\d+)</wp:posOffset>', chunk, re.DOTALL)
        cx = re.search(r'cx="(\d+)"', chunk)
        cy = re.search(r'cy="(\d+)"', chunk)
        print(img, rid, 'cx/cy', cx.group(1) if cx else '?', cy.group(1) if cy else '?')
        if pos_x:
            print('  x', pos_x.group(1))
        ys = re.findall(r'wp:posOffset[^>]*>(\d+)</wp:posOffset>', chunk)
        if ys:
            print('  offsets', ys)
