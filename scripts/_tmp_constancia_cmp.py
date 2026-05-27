import os
import re
import sys
import zipfile
from io import BytesIO

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from docx import Document

from core.pos.models import PaymentsCtaCollect
from core.pos.views.frm.ctascollect.constancia_xml_fill import fill_constancia_doc_paragraphs
from core.pos.views.frm.ctascollect.payment_constancia import (
    _constancia_context,
    constancia_template_path,
)

path = constancia_template_path()
with zipfile.ZipFile(path) as z:
    tpl_doc = z.read('word/document.xml').decode('utf-8', 'ignore')
    print('TEMPLATE embeds:', len(re.findall(r'r:embed', tpl_doc)))
    idx = tpl_doc.find('image3')
    print('image3 ctx:', tpl_doc[max(0, idx - 300) : idx + 100] if idx >= 0 else 'none')

p = PaymentsCtaCollect.objects.order_by('-id').first()
doc = Document(path)
fill_constancia_doc_paragraphs(doc, _constancia_context(p))
buf = BytesIO()
doc.save(buf)
with zipfile.ZipFile(buf) as z:
    saved = z.read('word/document.xml').decode('utf-8', 'ignore')
    print('AFTER SAVE embeds:', len(re.findall(r'r:embed', saved)))
    for m in re.finditer(r'r:embed="([^"]+)"', saved):
        rid = m.group(1)
        pos = m.start()
        snip = saved[max(0, pos - 400) : pos + 100]
        has_anchor = 'anchor' in snip or 'txbx' in snip
        print(rid, 'anchor' if has_anchor else 'inline', 'CHANCHA' in snip, 'distB' in snip)
