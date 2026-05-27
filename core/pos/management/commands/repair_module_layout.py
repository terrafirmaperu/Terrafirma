"""
Reasigna módulos a sus tipos correctos (Seguridad, Bodega, Facturación, etc.)
y elimina el tipo suelto «Asesoría y avances» si quedó vacío.

  python manage.py repair_module_layout
"""

from django.core.management.base import BaseCommand

from core.security.models import Module, ModuleType

LEGACY_TYPE_NAME = 'Asesoría y avances'

# Prefijos de URL por tipo (orden: el más específico primero si hiciera falta)
URL_PREFIX_BY_TYPE = (
    ('Seguridad', ('/security/', '/user/')),
    ('Bodega', ('/pos/scm/',)),
    ('Administrativo', ('/pos/frm/',)),
    ('Facturación', ('/pos/crm/',)),
    ('Reportes', ('/reports/',)),
)

HORIZONTAL_URLS = (
    '/pos/crm/sale/client/',
    '/user/update/password/',
    '/user/update/profile/',
    '/pos/crm/client/update/profile/',
    '/pos/crm/company/update/',
)


class Command(BaseCommand):
    help = 'Restaura la ubicación de módulos en el menú lateral.'

    def handle(self, *args, **options):
        types = {}
        for name, _ in URL_PREFIX_BY_TYPE:
            mt = ModuleType.objects.filter(name=name).first()
            if not mt:
                self.stdout.write(self.style.ERROR('Falta el tipo «{}». Ejecute core/tests.py.'.format(name)))
                return
            types[name] = mt

        moved = 0
        for module in Module.objects.all():
            url = module.url or ''
            if url in HORIZONTAL_URLS:
                if module.moduletype_id is not None or not module.is_vertical:
                    module.moduletype = None
                    module.is_vertical = False
                    module.save(update_fields=['moduletype', 'is_vertical'])
                    moved += 1
                continue

            target = None
            for type_name, prefixes in URL_PREFIX_BY_TYPE:
                if any(url.startswith(prefix) for prefix in prefixes):
                    target = types[type_name]
                    break

            if target and module.moduletype_id != target.pk:
                module.moduletype = target
                module.is_vertical = True
                module.save(update_fields=['moduletype', 'is_vertical'])
                moved += 1

        legacy = ModuleType.objects.filter(name=LEGACY_TYPE_NAME).first()
        if legacy:
            remaining = legacy.module_set.count()
            if remaining == 0:
                legacy.delete()
                self.stdout.write(self.style.WARNING('Eliminado tipo «{}».'.format(LEGACY_TYPE_NAME)))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        'El tipo «{}» aún tiene {} módulo(s); revise manualmente.'.format(
                            LEGACY_TYPE_NAME, remaining
                        )
                    )
                )

        order = list(ModuleType.objects.order_by('id').values_list('name', flat=True))
        self.stdout.write(self.style.SUCCESS('Módulos reasignados: {}. Orden de tipos: {}'.format(moved, order)))
