"""
Registra el módulo Control de Avance Asesoría bajo Facturación (mismo bloque CRM).

  python manage.py ensure_advisory_progress_module
  python manage.py ensure_advisory_progress_module --group-id 1
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from core.pos.models import AdvisoryProgressCase
from core.security.models import GroupModule, GroupPermission, Module, ModuleType

MODULE_TYPE_NAME = 'Facturación'
MODULE_URL = '/pos/crm/advisory/progress/'
LEGACY_MODULE_TYPE_NAME = 'Asesoría y avances'


class Command(BaseCommand):
    help = 'Crea el módulo de control de avance bajo el tipo Facturación.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--group-id',
            type=int,
            default=None,
            help='ID del grupo al que asignar permisos (por defecto el primer grupo).',
        )

    def handle(self, *args, **options):
        moduletype = ModuleType.objects.filter(name=MODULE_TYPE_NAME).first()
        if not moduletype:
            self.stdout.write(
                self.style.ERROR(
                    'No existe el tipo de módulo «{}». Ejecute el seed (core/tests.py) primero.'.format(
                        MODULE_TYPE_NAME
                    )
                )
            )
            return

        module, created = Module.objects.get_or_create(
            url=MODULE_URL,
            defaults={
                'name': 'Control de Avance Asesoría',
                'moduletype': moduletype,
                'description': 'Etapas de saneamiento visibles en el portal del cliente (2 a 9 etapas)',
                'icon': 'fas fa-route',
                'is_vertical': True,
                'is_visible': True,
                'is_active': True,
            },
        )
        module.name = 'Control de Avance Asesoría'
        module.moduletype = moduletype
        module.icon = 'fas fa-route'
        module.is_active = True
        module.is_visible = True
        module.is_vertical = True
        module.save()

        legacy_type = ModuleType.objects.filter(name=LEGACY_MODULE_TYPE_NAME).first()
        if legacy_type and legacy_type.pk != moduletype.pk:
            if not legacy_type.module_set.exclude(pk=module.pk).exists():
                legacy_type.delete()
                self.stdout.write(
                    self.style.WARNING('Eliminado tipo de módulo suelto «{}».'.format(LEGACY_MODULE_TYPE_NAME))
                )

        model_label = AdvisoryProgressCase._meta.label.split('.')[1].lower()
        perms = Permission.objects.filter(content_type__model=model_label)
        for p in perms:
            module.permits.add(p)

        group_id = options.get('group_id')
        group = Group.objects.filter(pk=group_id).first() if group_id else Group.objects.order_by('id').first()
        if not group:
            self.stdout.write(self.style.WARNING('No hay grupos. Cree uno y vuelva a ejecutar con --group-id.'))
            return

        GroupModule.objects.get_or_create(group=group, module=module)
        for perm in perms:
            GroupPermission.objects.get_or_create(
                group=group,
                permission=perm,
                defaults={'module': module},
            )

        action = 'Creado' if created else 'Actualizado'
        self.stdout.write(
            self.style.SUCCESS(
                '{action} módulo «{name}» en «{mtype}» ({url}) — grupo «{group}» (id={gid}).'.format(
                    action=action,
                    name=module.name,
                    mtype=moduletype.name,
                    url=MODULE_URL,
                    group=group.name,
                    gid=group.id,
                )
            )
        )
