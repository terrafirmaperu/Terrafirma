import re
import struct
import zipfile
from xml.etree import ElementTree as ET

path = r'core/pos/templates/frm/ctascollect/constancia_pago.docx'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

with zipfile.ZipFile(path) as z:
    print('all media:')
    for n in sorted(z.namelist()):
        if n.startswith('word/media/'):
            d = z.read(n)
            if d[:4] == b'\x89PNG':
                w, h = struct.unpack('>II', d[16:24])
                print(' ', n, w, h)
    print('--- document rels ---')
    doc = z.read('word/document.xml').decode('utf-8', 'ignore')
    rels = ET.fromstring(z.read('word/_rels/document.xml.rels').decode('utf-8'))
    rid_to_path = {}
    for rel in rels:
        t = rel.get('Target', '')
        if 'image' in rel.get('Type', '').lower():
            rid_to_path[rel.get('Id')] = 'word/' + t.lstrip('/')

    for rid, ip in sorted(rid_to_path.items()):
        if ip not in z.namelist():
            continue
        d = z.read(ip)
        w, h = struct.unpack('>II', d[16:24])
        # context in document.xml
        idx = doc.find(f'embed="{rid}"')
        if idx < 0:
            idx = doc.find(f'embed="{rid[3:]}"') if rid.startswith('rId') else -1
        snippet = doc[max(0, idx - 200) : idx + 200] if idx >= 0 else ''
        pos = 'footer' if 'footer' in snippet.lower() else (
            'anchor' if 'anchor' in snippet else 'inline'
        )
        print(ip, w, h, pos, 'txbx' in snippet)

    for hn in z.namelist():
        if 'header' in hn and hn.endswith('.xml'):
            ht = z.read(hn).decode('utf-8', 'ignore')
            for rid in rid_to_path:
                if rid in ht:
                    print('header uses', rid_to_path[rid], 'in', hn)
    print('--- paragraphs near firma ---')
    root = ET.fromstring(z.read('word/document.xml'))
    for p in root.iter(W + 'p'):
        t = ''.join(x.text or '' for x in p.findall('.//%st' % W))
        if any(k in t for k in ('CHANCHA', 'BUSSO', 'DNI', 'REPRESENTANTE', '____', 'ANA', 'PEREZ')):
            print(repr(t[:120]))
