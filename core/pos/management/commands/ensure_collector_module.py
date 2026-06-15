"""
Registra el módulo Admin Cobranzas bajo Administrativo.

  python manage.py ensure_collector_module
  python manage.py ensure_collector_module --group-id 1
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from core.pos.models import Collector
from core.security.models import GroupModule, GroupPermission, Module, ModuleType

MODULE_TYPE_NAME = 'Administrativo'
MODULE_URL = '/pos/frm/collector/'


class Command(BaseCommand):
    help = 'Crea el módulo de cobradores bajo el tipo Administrativo.'

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
                'name': 'Admin Cobranzas',
                'moduletype': moduletype,
                'description': 'Registro de cobradores asignados a ventas al crédito',
                'icon': 'fas fa-user-tag',
                'is_vertical': True,
                'is_visible': True,
                'is_active': True,
            },
        )
        module.name = 'Admin Cobranzas'
        module.moduletype = moduletype
        module.icon = 'fas fa-user-tag'
        module.is_active = True
        module.is_visible = True
        module.is_vertical = True
        module.save()

        model_label = Collector._meta.label.split('.')[1].lower()
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
        default_collector = Collector.get_or_create_default()
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
        self.stdout.write(
            self.style.SUCCESS(
                'Lugar de cobro predeterminado: «{}» (id={}).'.format(
                    default_collector.name,
                    default_collector.pk,
                )
            )
        )
