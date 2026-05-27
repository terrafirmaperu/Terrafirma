import os
import re
import struct
import sys
import zipfile
from io import BytesIO

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.pos.models import PaymentsCtaCollect
from core.pos.views.frm.ctascollect.payment_constancia import (
    build_constancia_docx,
    constancia_template_path,
)

p = PaymentsCtaCollect.objects.order_by('-id').first()
with open(constancia_template_path(), 'rb') as f:
    tpl = f.read()
out = build_constancia_docx(tpl, p)
with zipfile.ZipFile(BytesIO(out)) as z:
    print('media:')
    for n in sorted(z.namelist()):
        if n.startswith('word/media/'):
            d = z.read(n)
            if d[:4] == b'\x89PNG':
                w, h = struct.unpack('>II', d[16:24])
                print(n, w, h)
    doc = z.read('word/document.xml').decode('utf-8', 'ignore')
    for m in re.finditer(r'r:embed="rId\d+"', doc):
        print('embed', m.group())
    from xml.etree import ElementTree as ET
    W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    root = ET.fromstring(z.read('word/document.xml'))
    for p_el in root.iter(W + 'p'):
        t = ''.join(x.text or '' for x in p_el.findall('.//%st' % W))
        if 'CHANCHA' in t or 'PEREZ' in t or 'DNI' in t and len(t) < 80:
            print('P:', repr(t))
