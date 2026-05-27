# -*- coding: utf-8 -*-
"""Inserta marcadores de barcode y N° en el encabezado de constancia_pago.docx (una vez)."""
import os
import re
from zipfile import ZipFile, ZIP_DEFLATED

from django.conf import settings
from django.core.management.base import BaseCommand

MARK_BARCODE = '[[POLARISS_CONSTANCIA_BARCODE]]'
MARK_NUMBER = '[[POLARISS_CONSTANCIA_NRO]]'

HEADER_MARKER_BLOCK = (
    '<w:p>'
    '<w:pPr><w:jc w:val="left"/><w:spacing w:after="60"/></w:pPr>'
    '<w:r><w:t>{}</w:t></w:r>'
    '</w:p>'
    '<w:p>'
    '<w:pPr><w:jc w:val="right"/><w:spacing w:after="120"/></w:pPr>'
    '<w:r><w:t>{}</w:t></w:r>'
    '</w:p>'
).format(MARK_BARCODE, MARK_NUMBER)


class Command(BaseCommand):
    help = 'Añade marcadores de barcode y N° al encabezado de constancia_pago.docx'

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

        header_name = 'word/header2.xml'
        if header_name not in parts:
            self.stderr.write('Sin header2.xml')
            return

        xml = parts[header_name].decode('utf-8')
        if MARK_BARCODE in xml and MARK_NUMBER in xml:
            self.stdout.write(self.style.SUCCESS('La plantilla ya tiene marcadores en el encabezado.'))
            return

        insert_at = xml.find('>', xml.find('<w:hdr')) + 1
        if insert_at <= 0:
            self.stderr.write('No se pudo localizar w:hdr')
            return
        xml = xml[:insert_at] + HEADER_MARKER_BLOCK + xml[insert_at:]
        parts[header_name] = xml.encode('utf-8')

        tmp = path + '.tmp'
        with ZipFile(tmp, 'w', ZIP_DEFLATED) as zout:
            for name in names:
                zout.writestr(name, parts[name])
        os.replace(tmp, path)
        self.stdout.write(self.style.SUCCESS('Marcadores insertados en {}'.format(path)))
