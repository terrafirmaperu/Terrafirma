# -*- coding: utf-8 -*-
"""Quita marcadores POLARISS del encabezado (barcode/N° van abajo en el cuerpo)."""
import os
import re
from zipfile import ZipFile, ZIP_DEFLATED

from django.conf import settings
from django.core.management.base import BaseCommand

MARKERS = ('POLARISS_CONSTANCIA_BARCODE', 'POLARISS_CONSTANCIA_NRO')


class Command(BaseCommand):
    help = 'Elimina marcadores POLARISS de encabezados en constancia_pago.docx'

    def handle(self, *args, **options):
        path = os.path.join(
            settings.BASE_DIR,
            'core', 'pos', 'templates', 'frm', 'ctascollect', 'constancia_pago.docx',
        )
        if not os.path.isfile(path):
            self.stderr.write('No existe: {}'.format(path))
            return

        with ZipFile(path, 'r') as zin:
            names = zin.namelist()
            parts = {n: zin.read(n) for n in names}

        changed = False
        for name in list(parts.keys()):
            if not name.startswith('word/header') or not name.endswith('.xml'):
                continue
            txt = parts[name].decode('utf-8', 'ignore')
            if not any(m in txt for m in MARKERS):
                continue
            new_txt = re.sub(
                r'<w:p[^>]*>.*?POLARISS_CONSTANCIA_(?:BARCODE|NRO).*?</w:p>',
                '',
                txt,
                flags=re.DOTALL,
            )
            if new_txt != txt:
                parts[name] = new_txt.encode('utf-8')
                changed = True

        if not changed:
            self.stdout.write('Encabezados sin marcadores POLARISS (nada que limpiar).')
            return

        tmp = path + '.tmp'
        with ZipFile(tmp, 'w', ZIP_DEFLATED) as zout:
            for name in names:
                zout.writestr(name, parts[name])
        os.replace(tmp, path)
        self.stdout.write(self.style.SUCCESS('Encabezado limpiado: {}'.format(path)))
