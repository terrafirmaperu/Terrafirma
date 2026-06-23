import math
import os
import re
import unicodedata
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import FloatField
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.forms import model_to_dict
from django.utils import timezone

from config import settings
from core.pos.choices import (
    credit_down_payment_method,
    marital_status as marital_status_choices,
    payment_condition,
    payment_method,
    voucher,
)
from core.user.models import User


def _client_initial_letter(text):
    """Primera letra A–Z (sin tildes); si no aplica, 'X'."""
    if not text or not str(text).strip():
        return 'X'
    ch = unicodedata.normalize('NFD', str(text).strip()[0])[0]
    if not ch.isalpha():
        return 'X'
    return ch.upper()


def _client_public_code_prefix(client):
    """
    Tres letras: inicial departamento (ubigeo cliente), nombre, apellido paterno.
    """
    user = client.user
    dept = (client.department or client.predio_department or '').strip()
    d = _client_initial_letter(dept)
    n = _client_initial_letter((user.first_name or '').strip())
    ln = (user.last_name or '').strip()
    paternal_word = ln.split()[0] if ln else ''
    p = _client_initial_letter(paternal_word)
    return f'{d}{n}{p}'


class ClientCodeCounter(models.Model):
    """Una sola fila (pk=1): último correlativo global para códigos de cliente."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    last_seq = models.PositiveIntegerField(default=0, verbose_name='Último correlativo')

    class Meta:
        verbose_name = 'Contador código de cliente'
        verbose_name_plural = 'Contador códigos de cliente'


class PaymentConstanciaCounter(models.Model):
    """Una sola fila (pk=1): correlativo global de constancias de pago emitidas."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    last_number = models.PositiveIntegerField(default=0, verbose_name='Último N° de constancia')

    class Meta:
        verbose_name = 'Correlativo constancias de pago'
        verbose_name_plural = 'Correlativo constancias de pago'


class Company(models.Model):
    name = models.CharField(max_length=50, verbose_name='Nombre')
    ruc = models.CharField(max_length=13, verbose_name='Ruc')
    address = models.CharField(max_length=200, verbose_name='Dirección')
    mobile = models.CharField(max_length=10, verbose_name='Teléfono celular')
    phone = models.CharField(max_length=9, verbose_name='Teléfono convencional')
    email = models.CharField(max_length=50, verbose_name='Email')
    website = models.CharField(max_length=250, verbose_name='Página web')
    desc = models.CharField(max_length=500, null=True, blank=True, verbose_name='Descripción')
    image = models.ImageField(null=True, blank=True, upload_to='company/%Y/%m/%d', verbose_name='Logo')
    igv = models.DecimalField(default=0.00, decimal_places=2, max_digits=9, verbose_name='Igv')

    def __str__(self):
        return self.name

    def get_image(self):
        if self.image:
            return '{}{}'.format(settings.MEDIA_URL, self.image)
        return '{}{}'.format(settings.STATIC_URL, 'img/terrafirma_logo.svg')

    def get_comprobante_logo(self):
        """Logo institucional fijo para comprobantes PDF (no contratos Word)."""
        from core.pos.brand_assets import comprobante_logo_file_uri
        return comprobante_logo_file_uri()

    def get_igv(self):
        return format(self.igv, '.2f')

    def toJSON(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        default_permissions = ()
        permissions = (
            ('view_company', 'Can view Company'),
        )
        ordering = ['-id']


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Nombre')

    def __str__(self):
        return self.name

    def toJSON(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['-id']
        indexes = [
            models.Index(fields=['name'], name='pos_category_name_idx'),
        ]


class Product(models.Model):
    name = models.CharField(max_length=150, verbose_name='Nombre')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name='Categoría')
    price = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Precio de Compra')
    pvp = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Precio de Venta')
    image = models.ImageField(upload_to='product/%Y/%m/%d', verbose_name='Imagen', null=True, blank=True)

    def __str__(self):
        return self.name

    def remove_image(self):
        try:
            if self.image:
                os.remove(self.image.path)
        except:
            pass
        finally:
            self.image = None

    def toJSON(self):
        item = model_to_dict(self)
        item['category'] = self.category.toJSON()
        item['price'] = format(self.price, '.2f')
        item['price_promotion'] = format(self.get_price_promotion(), '.2f')
        item['price_current'] = format(self.get_price_current(), '.2f')
        item['pvp'] = format(self.pvp, '.2f')
        item['image'] = self.get_image()
        return item

    def get_price_promotion(self):
        promotions = self.promotionsdetail_set.filter(promotion__state=True)
        if promotions.exists():
            return promotions[0].price_final
        return 0.00

    def get_price_current(self):
        price_promotion = self.get_price_promotion()
        if price_promotion > 0:
            return price_promotion
        return self.pvp

    def get_image(self):
        if self.image:
            return '{}{}'.format(settings.MEDIA_URL, self.image)
        return '{}{}'.format(settings.STATIC_URL, 'img/default/empty.png')

    def delete(self, using=None, keep_parents=False):
        try:
            os.remove(self.image.path)
        except:
            pass
        super(Product, self).delete()

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['-name']
        indexes = [
            models.Index(fields=['name'], name='pos_product_name_idx'),
            models.Index(fields=['category', 'name'], name='pos_product_cat_name_idx'),
        ]


class ProductWorkerConfig(models.Model):
    """Cuotas de pago al obrero vinculadas al producto."""

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='worker_config',
        verbose_name='Producto',
    )
    quota_count = models.PositiveSmallIntegerField(
        default=1,
        verbose_name='Número de cuotas',
    )
    quota_amount = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        default=0.00,
        verbose_name='Monto por cuota',
    )
    inscription_amount = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        default=0.00,
        verbose_name='Inscripción',
    )
    quotas_enabled = models.BooleanField(
        default=False,
        verbose_name='Cuotas habilitadas',
    )

    def deliverables_total(self):
        total = self.product.worker_deliverables.aggregate(
            resp=models.Sum('charge_amount'),
        )['resp']
        return total if total is not None else Decimal('0.00')

    def worker_total(self):
        return self.inscription_amount + self.deliverables_total()

    def toJSON(self):
        return {
            'quota_count': self.quota_count,
            'quota_amount': format(self.quota_amount, '.2f'),
            'inscription_amount': format(self.inscription_amount, '.2f'),
            'quotas_enabled': self.quotas_enabled,
            'deliverables_total': format(self.deliverables_total(), '.2f'),
            'worker_total': format(self.worker_total(), '.2f'),
            'quota_total': format(self.quota_count * self.quota_amount, '.2f'),
        }

    class Meta:
        verbose_name = 'Configuración obrero (producto)'
        verbose_name_plural = 'Configuraciones obrero (producto)'


class ProductWorkerDeliverable(models.Model):
    """Entregable o proceso del obrero con monto de cobro, por producto."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='worker_deliverables',
        verbose_name='Producto',
    )
    order = models.PositiveSmallIntegerField(default=1, verbose_name='Orden')
    name = models.CharField(max_length=200, verbose_name='Entregable / proceso')
    charge_amount = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        default=0.00,
        verbose_name='Cobro',
    )
    notes = models.CharField(max_length=300, blank=True, default='', verbose_name='Notas')

    def toJSON(self):
        return {
            'id': self.id,
            'order': self.order,
            'name': self.name,
            'charge_amount': format(self.charge_amount, '.2f'),
            'notes': self.notes,
        }

    class Meta:
        verbose_name = 'Entregable obrero'
        verbose_name_plural = 'Entregables obrero'
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['product', 'order'], name='pos_worker_deliv_prod_ord'),
        ]


class Purchase(models.Model):
    payment_condition = models.CharField(choices=payment_condition, max_length=50, default='contado')
    date_joined = models.DateField(default=datetime.now)
    end_credit = models.DateField(default=datetime.now)
    subtotal = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)

    def __str__(self):
        return 'Compra {}'.format(format(self.id, '06d'))

    def calculate_invoice(self):
        subtotal = 0.00
        for d in self.purchasedetail_set.all():
            subtotal += float(d.price) * int(d.cant)
        self.subtotal = subtotal
        self.save()

    def delete(self, using=None, keep_parents=False):
        try:
            for i in self.purchasedetail_set.all():
                i.delete()
        except:
            pass
        super(Purchase, self).delete()

    def toJSON(self):
        item = model_to_dict(self)
        item['nro'] = format(self.id, '06d')
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['end_credit'] = self.end_credit.strftime('%Y-%m-%d')
        item['payment_condition'] = {'id': self.payment_condition, 'name': self.get_payment_condition_display()}
        item['subtotal'] = format(self.subtotal, '.2f')
        return item

    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        default_permissions = ()
        permissions = (
            ('view_purchase', 'Can view Compras'),
            ('add_purchase', 'Can add Compras'),
            ('delete_purchase', 'Can delete Compras'),
        )
        ordering = ['-id']


class PurchaseDetail(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    cant = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    dscto = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)

    def __str__(self):
        return self.product.name

    def toJSON(self):
        item = model_to_dict(self, exclude=['purchase'])
        item['product'] = self.product.toJSON()
        item['price'] = format(self.price, '.2f')
        item['dscto'] = format(self.dscto, '.2f')
        item['subtotal'] = format(self.subtotal, '.2f')
        return item

    class Meta:
        verbose_name = 'Detalle de Compra'
        verbose_name_plural = 'Detalle de Compras'
        permissions = ()
        ordering = ['-id']


class Client(models.Model):
    PREDIO_TYPE_CHOICES = (
        ('terreno', 'Terreno'),
        ('casa', 'Casa'),
        ('departamento', 'Departamento'),
        ('local_comercial', 'Local comercial'),
        ('otros', 'Otros'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mobile = models.CharField(max_length=10, verbose_name='Teléfono')
    marital_status = models.CharField(
        max_length=20,
        choices=marital_status_choices,
        blank=True,
        default='',
        verbose_name='Estado civil',
    )
    spouse_first_name = models.CharField(
        max_length=150, blank=True, default='', verbose_name='Nombres del cónyuge',
    )
    spouse_last_name = models.CharField(
        max_length=150, blank=True, default='', verbose_name='Apellidos del cónyuge',
    )
    spouse_dni = models.CharField(
        max_length=12, blank=True, default='', verbose_name='DNI del cónyuge',
    )
    marriage_certificate = models.FileField(
        upload_to='client/marriage/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Acta de matrimonio',
    )
    death_certificate = models.FileField(
        upload_to='client/death/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Acta de defunción',
    )
    divorce_certificate = models.FileField(
        upload_to='client/divorce/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Documento de divorcio',
    )
    separation_certificate = models.FileField(
        upload_to='client/separation/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Documento de separación',
    )
    department = models.CharField(max_length=80, null=True, blank=True, verbose_name='Departamento')
    province = models.CharField(max_length=80, null=True, blank=True, verbose_name='Provincia')
    district = models.CharField(max_length=80, null=True, blank=True, verbose_name='Distrito')
    #birthdate = models.DateField(default=datetime.now, verbose_name='Fecha de nacimiento')
    address = models.CharField(max_length=500, null=True, blank=True, verbose_name='Dirección')
    has_predio = models.BooleanField(default=False, verbose_name='Vincular a predio')
    predio_department = models.CharField(max_length=80, null=True, blank=True, verbose_name='Departamento del predio')
    predio_province = models.CharField(max_length=80, null=True, blank=True, verbose_name='Provincia del predio')
    predio_district = models.CharField(max_length=80, null=True, blank=True, verbose_name='Distrito del predio')
    predio_address = models.CharField(max_length=500, null=True, blank=True, verbose_name='Dirección del predio')
    predio_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='Área aproximada')
    predio_perimeter = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='Perímetro')
    predio_lot_number = models.CharField(max_length=30, null=True, blank=True, verbose_name='Número de lote')
    predio_block = models.CharField(max_length=30, null=True, blank=True, verbose_name='Manzana')
    predio_registry_number = models.CharField(max_length=50, null=True, blank=True, verbose_name='Número de partida del predio')
    predio_type = models.CharField(
        max_length=30,
        choices=PREDIO_TYPE_CHOICES,
        null=True,
        blank=True,
        verbose_name='Tipo de predio',
    )
    client_code = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        blank=True,
        verbose_name='Código de cliente',
        help_text='Letras (depto + nombre + apellido paterno) + 5 cifras correlativas. No se modifica tras asignar.',
    )

    def __str__(self):
        return '{} / {}'.format(self.user.get_full_name(), self.user.dni)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.client_code:
            return
        prefix = _client_public_code_prefix(self)
        with transaction.atomic():
            ctr, _ = ClientCodeCounter.objects.select_for_update().get_or_create(
                pk=1,
                defaults={'last_seq': 0},
            )
            ctr.last_seq += 1
            ctr.save(update_fields=['last_seq'])
            seq = ctr.last_seq
            new_code = '{}{:05d}'.format(prefix, seq)
            Client.objects.filter(pk=self.pk).update(client_code=new_code)
        self.client_code = new_code

    '''def birthdate_format(self):
        return self.birthdate.strftime('%Y-%m-%d')'''

    def toJSON(self):
        item = model_to_dict(self, exclude=['user'])
        item['user'] = self.user.toJSON()
        item['id'] = self.id
        item['mobile'] = self.mobile if self.mobile else ''
        item['marital_status'] = {
            'id': self.marital_status or '',
            'name': self.get_marital_status_display() if self.marital_status else '',
        }
        item['spouse'] = {
            'first_name': self.spouse_first_name or '',
            'last_name': self.spouse_last_name or '',
            'dni': self.spouse_dni or '',
            'full_name': ' '.join(
                p for p in (self.spouse_first_name or '', self.spouse_last_name or '') if p
            ).strip(),
        }
        item['marriage_certificate'] = (
            self.marriage_certificate.url if self.marriage_certificate else ''
        )
        item['death_certificate'] = (
            self.death_certificate.url if self.death_certificate else ''
        )
        item['divorce_certificate'] = (
            self.divorce_certificate.url if self.divorce_certificate else ''
        )
        item['separation_certificate'] = (
            self.separation_certificate.url if self.separation_certificate else ''
        )
        item['department'] = self.department if self.department else ''
        item['province'] = self.province if self.province else ''
        item['district'] = self.district if self.district else ''
        item['address'] = self.address if self.address else ''
        item['has_predio'] = bool(self.has_predio)
        item['predio_department'] = self.predio_department if self.predio_department else ''
        item['predio_province'] = self.predio_province if self.predio_province else ''
        item['predio_district'] = self.predio_district if self.predio_district else ''
        item['predio_address'] = self.predio_address if self.predio_address else ''
        item['predio_area'] = '' if self.predio_area is None else format(self.predio_area, '.2f')
        item['predio_perimeter'] = '' if self.predio_perimeter is None else format(self.predio_perimeter, '.2f')
        item['predio_lot_number'] = self.predio_lot_number if self.predio_lot_number else ''
        item['predio_block'] = self.predio_block if self.predio_block else ''
        item['predio_registry_number'] = self.predio_registry_number if self.predio_registry_number else ''
        item['predio_type'] = {
            'id': self.predio_type or '',
            'name': self.get_predio_type_display() if self.predio_type else '',
        }
        item['client_code'] = self.client_code or ''
        from core.pos.client_properties import client_property_to_dict
        item['properties'] = [
            client_property_to_dict(p)
            for p in self.properties.order_by('order', 'id')
        ]
        if not item['properties'] and self.has_predio:
            from core.pos.client_properties import legacy_client_to_property_dict
            item['properties'] = [legacy_client_to_property_dict(self)]
        return item

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'


class ClientProperty(models.Model):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='properties',
        verbose_name='Cliente',
    )
    label = models.CharField(max_length=120, blank=True, verbose_name='Nombre / referencia')
    department = models.CharField(max_length=80, blank=True, verbose_name='Departamento')
    province = models.CharField(max_length=80, blank=True, verbose_name='Provincia')
    district = models.CharField(max_length=80, blank=True, verbose_name='Distrito')
    community_location_enabled = models.BooleanField(
        default=False,
        verbose_name='Registrar comunidad / centro poblado',
    )
    community = models.CharField(max_length=120, blank=True, verbose_name='Comunidad')
    population_center = models.CharField(max_length=200, blank=True, verbose_name='Centro poblado')
    address = models.CharField(max_length=500, blank=True, verbose_name='Dirección')
    area = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='Área aproximada',
    )
    perimeter = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='Perímetro',
    )
    lot_number = models.CharField(max_length=30, blank=True, verbose_name='Número de lote')
    block = models.CharField(max_length=30, blank=True, verbose_name='Manzana')
    registry_number = models.CharField(max_length=50, blank=True, verbose_name='Número de partida')
    predio_type = models.CharField(
        max_length=30,
        choices=Client.PREDIO_TYPE_CHOICES,
        null=True,
        blank=True,
        verbose_name='Tipo de predio',
    )
    is_primary = models.BooleanField(default=False, verbose_name='Predio principal')
    order = models.PositiveSmallIntegerField(default=0, verbose_name='Orden')
    product = models.ForeignKey(
        'Product',
        on_delete=models.PROTECT,
        related_name='client_properties',
        null=True,
        blank=True,
        verbose_name='Producto / servicio a facturar',
    )
    contract_locked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Contrato generado (bloqueo de desvinculación)',
    )

    @property
    def is_contract_locked(self):
        return self.contract_locked_at is not None

    def __str__(self):
        parts = [self.label] if self.label else []
        if self.lot_number:
            parts.append('Lote {}'.format(self.lot_number))
        if self.district:
            parts.append(self.district)
        return ' — '.join(parts) or 'Predio #{}'.format(self.pk)

    class Meta:
        verbose_name = 'Predio del cliente'
        verbose_name_plural = 'Predios del cliente'
        ordering = ['order', 'id']
        permissions = (
            ('unlock_contract_predio', 'Autorizar desvinculación de predios con contrato'),
        )


class Collector(models.Model):
    DEFAULT_NAME = 'Oficina'

    name = models.CharField(max_length=200, unique=True, verbose_name='Nombre')
    is_active = models.BooleanField(default=True, verbose_name='Activo')

    def __str__(self):
        return self.name

    def get_full_name(self):
        return self.name

    @classmethod
    def get_or_create_default(cls):
        obj, _ = cls.objects.get_or_create(
            name=cls.DEFAULT_NAME,
            defaults={'is_active': True},
        )
        if not obj.is_active:
            obj.is_active = True
            obj.save(update_fields=['is_active'])
        return obj

    def toJSON(self):
        return {
            'id': self.id,
            'name': self.name,
            'full_name': self.name,
            'is_active': self.is_active,
        }

    class Meta:
        verbose_name = 'Cobrador'
        verbose_name_plural = 'Cobradores'
        ordering = ['name', 'id']


class Sale(models.Model):
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True)
    employee = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    collector = models.ForeignKey(
        Collector,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name='Cobrador',
    )
    payment_condition = models.CharField(choices=payment_condition, max_length=50, default='contado')
    payment_method = models.CharField(choices=payment_method, max_length=50, default='efectivo')
    type_voucher = models.CharField(choices=voucher, max_length=50, default='ticket')
    date_joined = models.DateField(default=timezone.localdate)
    end_credit = models.DateField(default=timezone.localdate)
    credit_quota_count = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Número de cuotas',
        help_text='Cuotas programadas (1 a 5), sin contar el pago inicial.',
    )
    credit_down_payment = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        default=0.00,
        verbose_name='Inicial',
    )
    credit_down_payment_method = models.CharField(
        choices=credit_down_payment_method,
        max_length=50,
        default='efectivo',
        verbose_name='Inicial pagada con',
    )
    quota_plan_override = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Plan de cuotas personalizado',
        help_text='Cuotas editadas por administrador en cuentas por cobrar.',
    )
    subtotal = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    dscto = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    total_dscto = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    igv = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    total_igv = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    cash = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    change = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    card_number = models.CharField(max_length=30, null=True, blank=True)
    titular = models.CharField(max_length=30, null=True, blank=True)
    amount_debited = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    cash_register_session = models.ForeignKey(
        'CashRegisterSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name='Sesión de caja',
    )
    sale_code = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        blank=True,
        verbose_name='Código de venta',
        help_text='Identificador único interno (VT-######), asignado al guardar.',
    )
    contract_code = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        blank=True,
        verbose_name='Código de contrato',
        help_text='Un contrato por venta (CT-######), asignado al guardar.',
    )
    is_voided = models.BooleanField(default=False, verbose_name='Anulada')
    voided_at = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de anulación')
    voided_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voided_sales',
        verbose_name='Anulada por',
    )

    def __str__(self):
        return f'{self.client.user.get_full_name()} / {self.nro()}'

    def nro(self):
        return format(self.id, '06d')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        sale_code = 'VT-{:06d}'.format(self.id)
        contract_code = 'CT-{:06d}'.format(self.id)
        if self.sale_code != sale_code or self.contract_code != contract_code:
            Sale.objects.filter(pk=self.pk).update(
                sale_code=sale_code,
                contract_code=contract_code,
            )
            self.sale_code = sale_code
            self.contract_code = contract_code

    def get_client(self):
        if self.client:
            return self.client.toJSON()
        return {}

    def card_number_format(self):
        if self.card_number:
            cardnumber = self.card_number.split(' ')
            convert = re.sub('[0-9]', 'X', ' '.join(cardnumber[1:]))
            return '{} {}'.format(cardnumber[0], convert)
        return self.card_number

    def contract_docx_basename(self):
        """Nombre de archivo del contrato en Word (.docx), mismo criterio que la vista de descarga."""
        cc = self.contract_code or ('CT-{:06d}'.format(self.id) if self.id else 'CT-000000')
        safe_cc = cc.replace('/', '-').replace('\\', '-')
        client = self.client
        if client is None and self.client_id:
            client = Client.objects.select_related('user').filter(pk=self.client_id).first()
        user = client.user if client else None
        dni = (user.dni if user else '').strip() or '00000000'
        return 'CONTRATO_{}_{}.docx'.format(safe_cc, dni)

    def toJSON(self):
        # Dict explícito (sin model_to_dict): evita Decimal/date/FK residuales que rompen json.dumps.
        item = {
            'id': self.id,
            'nro': format(self.id, '06d'),
            'sale_code': self.sale_code or '',
            'contract_code': self.contract_code or '',
            'contract_docx_basename': self.contract_docx_basename(),
            'card_number': self.card_number_format(),
            'titular': self.titular or '',
            'date_joined': self.date_joined.strftime('%Y-%m-%d'),
            'end_credit': self.end_credit.strftime('%Y-%m-%d'),
            'employee': {} if self.employee is None else self.employee.toJSON(),
            'collector': {} if self.collector is None else self.collector.toJSON(),
            'client': {} if self.client is None else self.client.toJSON(),
            'payment_condition': {
                'id': self.payment_condition,
                'name': self.get_payment_condition_display(),
            },
            'payment_method': {
                'id': self.payment_method,
                'name': self.get_payment_method_display(),
            },
            'type_voucher': {
                'id': self.type_voucher,
                'name': self.get_type_voucher_display(),
            },
            'subtotal': format(self.subtotal, '.2f'),
            'dscto': format(self.dscto, '.2f'),
            'total_dscto': format(self.total_dscto, '.2f'),
            'igv': format(self.igv, '.2f'),
            'total_igv': format(self.total_igv, '.2f'),
            'total': format(self.total, '.2f'),
            'cash': format(self.cash, '.2f'),
            'change': format(self.change, '.2f'),
            'amount_debited': format(self.amount_debited, '.2f'),
            'credit_quota_count': self.credit_quota_count,
            'credit_down_payment': format(self.credit_down_payment, '.2f'),
            'credit_down_payment_method': {
                'id': self.credit_down_payment_method,
                'name': self.get_credit_down_payment_method_display(),
            },
            'cash_register_session_id': self.cash_register_session_id,
            'is_voided': bool(self.is_voided),
            'voided_at': self.voided_at.strftime('%Y-%m-%d %H:%M') if self.voided_at else '',
        }
        return item

    def calculate_invoice(self):
        from core.pos.tax import split_tax_inclusive

        inclusive_sum = 0.00
        for d in self.saledetail_set.filter():
            d.subtotal = float(d.price) * int(d.cant)
            d.total_dscto = float(d.dscto) * float(d.subtotal)
            d.total = d.subtotal - d.total_dscto
            d.save()
            inclusive_sum += d.total
        self.total_dscto = inclusive_sum * float(self.dscto)
        amount_payable = float(inclusive_sum) - float(self.total_dscto)
        rate = float(self.igv)
        if rate > 0:
            base, tax = split_tax_inclusive(amount_payable, rate)
            self.subtotal = float(base)
            self.total_igv = float(tax)
        else:
            self.subtotal = amount_payable
            self.total_igv = 0.00
        self.total = amount_payable
        self.save()

    def igv_percent_display(self):
        """Porcentaje IGV para impresión (sale.igv se guarda como 0.18)."""
        return float(self.igv) * 100 if float(self.igv) < 1 else float(self.igv)

    def delete(self, using=None, keep_parents=False):
        try:
            for i in self.saledetail_set.filter():
                i.delete()
        except:
            pass
        super(Sale, self).delete()

    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        default_permissions = ()
        permissions = (
            ('view_sale', 'Can view Ventas'),
            ('add_sale', 'Can add Ventas'),
            ('delete_sale', 'Can delete Ventas'),
        )
        ordering = ['-id']


class SaleDetail(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    client_property = models.ForeignKey(
        'ClientProperty',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sale_details',
        verbose_name='Predio vinculado',
    )
    cant = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    dscto = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    total_dscto = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)

    def __str__(self):
        return self.product.name

    def toJSON(self):
        item = model_to_dict(self, exclude=['sale'])
        item['product'] = self.product.toJSON()
        item['price'] = format(self.price, '.2f')
        item['dscto'] = format(self.dscto, '.2f')
        item['total_dscto'] = format(self.total_dscto, '.2f')
        item['subtotal'] = format(self.subtotal, '.2f')
        item['total'] = format(self.total, '.2f')
        return item

    class Meta:
        verbose_name = 'Detalle de Venta'
        verbose_name_plural = 'Detalle de Ventas'
        default_permissions = ()
        ordering = ['-id']


def _split_amount_in_equal_quotas(total: Decimal, parts: int):
    """Reparte `total` en `parts` partes en céntimos; el resto se reparte en las primeras cuotas."""
    if parts <= 0:
        return []
    total = total.quantize(Decimal('0.01'))
    if total <= 0:
        return [Decimal('0.00')] * parts
    cents = int((total * 100).to_integral_value(rounding=ROUND_DOWN))
    q, r = divmod(cents, parts)
    out = []
    for i in range(parts):
        c = q + (1 if i < r else 0)
        out.append(Decimal(c) / Decimal(100))
    return out


class CtasCollect(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT)
    date_joined = models.DateField(default=datetime.now)
    end_date = models.DateField(default=datetime.now)
    debt = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    saldo = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    state = models.BooleanField(default=True)

    def __str__(self):
        return '{} / {} / S/  {}'.format(self.sale.client.user.get_full_name(), self.date_joined.strftime('%Y-%m-%d'),
                                      format(self.debt, '.2f'))

    def get_quota_plan(self):
        """
        Plan de pagos: inicial (si aplica) y cuotas 1..N.
        Usa override de venta si fue ajustado por administrador.
        """
        sale = self.sale
        override = sale.quota_plan_override
        if override:
            return list(override)

        from datetime import timedelta
        if sale.payment_condition != 'credito':
            return []
        total = Decimal(str(sale.total)).quantize(Decimal('0.01'))
        inicial = Decimal(str(sale.credit_down_payment or 0)).quantize(Decimal('0.01'))
        n = max(1, int(sale.credit_quota_count or 1))
        financed = (total - inicial).quantize(Decimal('0.01'))
        if financed < 0:
            financed = Decimal('0.00')

        base_date = sale.date_joined
        plan = []
        if inicial > 0:
            plan.append({
                'num': 0,
                'label': 'Inicial',
                'amount': format(inicial, '.2f'),
                'due_date': base_date.strftime('%Y-%m-%d'),
            })
        amounts = _split_amount_in_equal_quotas(financed, n)
        end_date = sale.end_credit
        diff_days = (end_date - base_date).days if end_date and base_date else 25 * n
        if diff_days <= 0:
            diff_days = 25 * n
        for i in range(1, n + 1):
            amt = amounts[i - 1] if i - 1 < len(amounts) else Decimal('0.00')
            step_days = round((diff_days * i) / n)
            due = base_date + timedelta(days=step_days)
            plan.append({
                'num': i,
                'label': 'Cuota {}'.format(i),
                'amount': format(amt, '.2f'),
                'due_date': due.strftime('%Y-%m-%d'),
            })
        return plan

    def validate_debt(self):
        try:
            saldo = self.paymentsctacollect_set.aggregate(resp=Coalesce(Sum('valor'), 0.00, output_field=FloatField())).get('resp')
            self.saldo = float(self.debt) - float(saldo)
            self.state = self.saldo > 0.00
            self.save()
        except:
            pass

    def toJSON(self):
        from core.pos.advisory_sale_cases import build_sale_predio_summary_from_sale

        item = model_to_dict(self)
        item['sale'] = self.sale.toJSON()
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['end_date'] = self.end_date.strftime('%Y-%m-%d')
        item['debt'] = format(self.debt, '.2f')
        item['saldo'] = format(self.saldo, '.2f')
        total_d = Decimal(str(self.sale.total))
        inicial_d = Decimal(str(self.sale.credit_down_payment or 0))
        item['credit_quota_count'] = self.sale.credit_quota_count
        item['credit_down_payment'] = format(inicial_d, '.2f')
        item['financed_balance'] = format(max(Decimal('0'), total_d - inicial_d), '.2f')
        item['quota_plan'] = self.get_quota_plan()
        item['predio_reference'] = build_sale_predio_summary_from_sale(self.sale) if self.sale_id else ''
        from core.pos.product_worker import worker_entregables_for_sale
        item['worker_entregables'] = worker_entregables_for_sale(self.sale)
        return item

    class Meta:
        verbose_name = 'Cuenta por cobrar'
        verbose_name_plural = 'Cuentas por cobrar'
        default_permissions = ()
        permissions = (
            ('view_ctascollect', 'Can view Cuentas por cobrar'),
            ('add_ctascollect', 'Can add Cuentas por cobrar'),
            ('delete_ctascollect', 'Can delete Cuentas por cobrar'),
        )
        ordering = ['-id']


class PaymentsCtaCollect(models.Model):
    ctascollect = models.ForeignKey(CtasCollect, on_delete=models.CASCADE)
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    desc = models.CharField(max_length=500, null=True, blank=True, verbose_name='Detalles')
    valor = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Valor')
    cash_register_session = models.ForeignKey(
        'CashRegisterSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments_ctacollect',
        verbose_name='Sesión de caja',
    )
    constancia_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name='N° constancia de pago',
    )
    payment_method = models.CharField(
        max_length=50,
        choices=credit_down_payment_method,
        default='efectivo',
        verbose_name='Forma de pago',
    )
    collector = models.ForeignKey(
        Collector,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name='Lugar de cobro',
    )
    worker_deliverable = models.ForeignKey(
        'ProductWorkerDeliverable',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ctacollect_payments',
        verbose_name='Entregable / proceso',
    )
    worker_inscription_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='worker_inscription_payments',
        verbose_name='Inscripción (producto)',
    )

    def worker_entregable_label(self):
        if self.worker_deliverable_id:
            d = self.worker_deliverable
            return '{} — {}'.format(d.product.name, d.name)
        if self.worker_inscription_product_id:
            return '{} — Inscripción'.format(self.worker_inscription_product.name)
        return ''

    def __str__(self):
        return self.ctascollect.id

    def allocate_constancia_number(self):
        """Asigna correlativo único (9 dígitos en impresión); no cambia si ya existe."""
        if self.constancia_number:
            return self.constancia_number
        with transaction.atomic():
            locked = PaymentsCtaCollect.objects.select_for_update().get(pk=self.pk)
            if locked.constancia_number:
                self.constancia_number = locked.constancia_number
                return locked.constancia_number
            ctr, _ = PaymentConstanciaCounter.objects.select_for_update().get_or_create(
                pk=1,
                defaults={'last_number': 0},
            )
            ctr.last_number += 1
            ctr.save(update_fields=['last_number'])
            locked.constancia_number = ctr.last_number
            locked.save(update_fields=['constancia_number'])
            self.constancia_number = locked.constancia_number
            return locked.constancia_number

    def toJSON(self):
        item = model_to_dict(self, exclude=['ctascollect'])
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['valor'] = format(self.valor, '.2f')
        item['constancia_number'] = self.constancia_number
        item['payment_method'] = {
            'id': self.payment_method,
            'name': self.get_payment_method_display(),
        }
        item['collector'] = {} if self.collector is None else self.collector.toJSON()
        label = self.worker_entregable_label()
        item['worker_entregable'] = {
            'label': label,
            'type': 'inscription' if self.worker_inscription_product_id else (
                'deliverable' if self.worker_deliverable_id else ''
            ),
        }
        return item

    class Meta:
        verbose_name = 'Pago Cuenta por cobrar'
        verbose_name_plural = 'Pagos Cuentas por cobrar'
        default_permissions = ()
        ordering = ['-id']


class DebtsPay(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT)
    date_joined = models.DateField(default=datetime.now)
    end_date = models.DateField(default=datetime.now)
    debt = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    saldo = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    state = models.BooleanField(default=True)

    def __str__(self):
        return 'Compra {} / {} / ${}'.format(format(self.purchase.id, '06d'), self.date_joined.strftime('%Y-%m-%d'),
                                      format(self.debt, '.2f'))

    def validate_debt(self):
        try:
            saldo = self.paymentsdebtspay_set.aggregate(resp=Coalesce(Sum('valor'), 0.00, output_field=FloatField())).get('resp')
            self.saldo = float(self.debt) - float(saldo)
            self.state = self.saldo > 0.00
            self.save()
        except:
            pass

    @staticmethod
    def _quota_label(num):
        suffix = 'ta'
        if num in (1, 3):
            suffix = 'ra'
        elif num == 2:
            suffix = 'da'
        return '{}{} cuota'.format(num, suffix)

    def get_current_quota_label(self):
        if not self.state or float(self.saldo or 0) <= 0:
            return 'Pagado'
        paid_count = self.paymentsdebtspay_set.count()
        current = max(1, paid_count + 1)
        return self._quota_label(current)

    def toJSON(self):
        item = model_to_dict(self)
        item['purchase'] = self.purchase.toJSON()
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['end_date'] = self.end_date.strftime('%Y-%m-%d')
        item['debt'] = format(self.debt, '.2f')
        item['saldo'] = format(self.saldo, '.2f')
        item['current_quota_label'] = self.get_current_quota_label()
        return item

    class Meta:
        verbose_name = 'Cuenta por pagar'
        verbose_name_plural = 'Cuentas por pagar'
        default_permissions = ()
        permissions = (
            ('view_debtspay', 'Can view Cuentas por pagar'),
            ('add_debtspay', 'Can add Cuentas por pagar'),
            ('delete_debtspay', 'Can delete Cuentas por pagar'),
        )
        ordering = ['-id']


class PaymentsDebtsPay(models.Model):
    debtspay = models.ForeignKey(DebtsPay, on_delete=models.CASCADE)
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de registro')
    desc = models.CharField(max_length=500, null=True, blank=True, verbose_name='Detalles')
    valor = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Valor')

    def __str__(self):
        return self.debtspay.id

    def toJSON(self):
        item = model_to_dict(self, exclude=['debtspay'])
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['valor'] = format(self.valor, '.2f')
        return item

    class Meta:
        verbose_name = 'Det. Cuenta por pagar'
        verbose_name_plural = 'Det. Cuentas por pagar'
        default_permissions = ()
        ordering = ['-id']


class TypeExpense(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Nombre')

    def __str__(self):
        return self.name

    def toJSON(self):
        item = model_to_dict(self)
        return item

    class Meta:
        verbose_name = 'Tipo de Gasto'
        verbose_name_plural = 'Tipos de Gastos'
        ordering = ['id']


class Expenses(models.Model):
    typeexpense = models.ForeignKey(TypeExpense, verbose_name='Tipo de Gasto', on_delete=models.PROTECT)
    desc = models.CharField(max_length=500, null=True, blank=True, verbose_name='Descripción')
    date_joined = models.DateField(default=datetime.now, verbose_name='Fecha de Registro')
    valor = models.DecimalField(max_digits=9, decimal_places=2, default=0.00, verbose_name='Valor')
    cash_register_session = models.ForeignKey(
        'CashRegisterSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses',
        verbose_name='Sesión de caja',
    )

    def __str__(self):
        return self.desc

    def get_desc(self):
        if self.desc:
            return self.desc
        return 'Sin detalles'

    def toJSON(self):
        item = model_to_dict(self)
        item['typeexpense'] = self.typeexpense.toJSON()
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['valor'] = format(self.valor, '.2f')
        item['desc'] = self.get_desc()
        return item

    class Meta:
        verbose_name = 'Gasto'
        verbose_name_plural = 'Gastos'
        ordering = ['id']


class Promotions(models.Model):
    start_date = models.DateField(default=datetime.now)
    end_date = models.DateField(default=datetime.now)
    state = models.BooleanField(default=True)

    def __str__(self):
        return str(self.id)

    def toJSON(self):
        item = model_to_dict(self)
        item['start_date'] = self.start_date.strftime('%Y-%m-%d')
        item['end_date'] = self.end_date.strftime('%Y-%m-%d')
        return item

    class Meta:
        verbose_name = 'Promoción'
        verbose_name_plural = 'Promociones'
        ordering = ['-id']


class PromotionsDetail(models.Model):
    promotion = models.ForeignKey(Promotions, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    price_current = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    dscto = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    total_dscto = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    price_final = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)

    def __str__(self):
        return self.product.name

    def get_dscto_real(self):
        total_dscto = float(self.price_current) * float(self.dscto)
        n = 2
        return math.floor(total_dscto * 10 ** n) / 10 ** n

    def toJSON(self):
        item = model_to_dict(self, exclude=['promotion'])
        item['product'] = self.product.toJSON()
        item['price_current'] = format(self.price_current, '.2f')
        item['dscto'] = format(self.dscto, '.2f')
        item['total_dscto'] = format(self.total_dscto, '.2f')
        item['price_final'] = format(self.price_final, '.2f')
        return item

    class Meta:
        verbose_name = 'Detalle Promoción'
        verbose_name_plural = 'Detalle de Promociones'
        ordering = ['-id']
        indexes = [
            models.Index(
                fields=['product', 'promotion'],
                name='pos_promodetail_prod_prom_idx',
            ),
        ]


class Devolution(models.Model):
    saledetail = models.ForeignKey(SaleDetail, on_delete=models.PROTECT)
    date_joined = models.DateField(default=datetime.now)
    cant = models.IntegerField(default=0)
    motive = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return self.motive

    def toJSON(self):
        item = model_to_dict(self)
        item['date_joined'] = self.date_joined.strftime('%Y-%m-%d')
        item['saledetail'] = self.saledetail.toJSON()
        item['motive'] = 'Sin detalles' if len(self.motive) == 0 else self.motive
        return item

    class Meta:
        verbose_name = 'Cancelación'
        verbose_name_plural = 'Cancelaciones'
        default_permissions = ()
        permissions = (
            ('view_devolution', 'Can view Cancelaciones'),
            ('add_devolution', 'Can add Cancelaciones'),
            ('delete_devolution', 'Can delete Cancelaciones'),
        )
        ordering = ['-id']


class CashRegisterSession(models.Model):
    OPEN = 'abierta'
    CLOSED = 'cerrada'
    STATUS_CHOICES = (
        (OPEN, 'Abierta'),
        (CLOSED, 'Cerrada'),
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Empresa',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=OPEN,
        verbose_name='Estado',
    )
    opened_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha y hora de apertura',
    )
    opening_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Monto inicial de caja',
    )
    user_opened = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='cash_sessions_opened',
        verbose_name='Usuario apertura',
    )
    close_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha y hora de cierre',
    )
    closing_amount_counted = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Monto contado al cierre',
    )
    closing_amount_expected = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Monto esperado al cierre',
    )
    difference_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Diferencia (contado - esperado)',
    )
    user_closed = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cash_sessions_closed',
        verbose_name='Usuario cierre',
    )
    observations = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name='Observaciones',
    )

    def __str__(self):
        return 'Caja #{0} - {1}'.format(self.pk or '-', self.get_status_display())

    @classmethod
    def get_open_session(cls):
        """Caja única del sistema: a lo sumo una sesión abierta."""
        return cls.objects.filter(status=cls.OPEN).order_by('-opened_at', '-id').first()

    def opened_by(self, user):
        return bool(user and self.user_opened_id and self.user_opened_id == user.id)

    def toJSON(self):
        item = model_to_dict(self, exclude=['company', 'user_opened', 'user_closed'])
        item['company'] = self.company_id
        item['user_opened'] = self.user_opened_id
        item['user_closed'] = self.user_closed_id
        item['user_opened_name'] = (
            self.user_opened.get_full_name() if self.user_opened_id else ''
        )
        item['status'] = self.status
        if self.opened_at:
            item['opened_at'] = self.opened_at.strftime('%Y-%m-%d %H:%M:%S')
        if self.close_at:
            item['close_at'] = self.close_at.strftime('%Y-%m-%d %H:%M:%S')
        for fname in ('opening_amount', 'closing_amount_counted', 'closing_amount_expected', 'difference_amount'):
            val = item.get(fname)
            if val is not None:
                item[fname] = format(val, '.2f')
        return item

    class Meta:
        verbose_name = 'Sesión de caja'
        verbose_name_plural = 'Sesiones de caja'
        default_permissions = ()
        permissions = (
            ('view_cashregistersession', 'Can view Sesión de caja'),
            ('add_cashregistersession', 'Can add Sesión de caja'),
            ('change_cashregistersession', 'Can change Sesión de caja'),
            ('delete_cashregistersession', 'Can delete Sesión de caja'),
        )
        ordering = ['-opened_at', '-id']


ADVISORY_STAGE_MIN = 2
ADVISORY_STAGE_MAX = 9

ADVISORY_DEFAULT_STAGE_TITLES = (
    'Recepción de expediente',
    'Estudio técnico y legal',
    'Saneamiento físico / topografía',
    'Elaboración de documentos',
    'Gestión municipal',
    'Presentación registral',
    'Seguimiento registral',
    'Inscripción registral',
    'Entrega de títulos',
)


class AdvisoryProgressCase(models.Model):
    """Caso de asesoría / saneamiento de un predio, visible en el portal del cliente."""

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='advisory_cases',
        verbose_name='Cliente',
    )
    sale = models.OneToOneField(
        'Sale',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='advisory_case',
        verbose_name='Venta / contrata',
        help_text='Cada contrata generada crea un caso vinculado a la venta.',
    )
    title = models.CharField(max_length=200, verbose_name='Terreno / caso')
    predio_summary = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Resumen ubicación',
        help_text='Opcional. Se puede completar desde los datos del predio del cliente.',
    )
    total_stages = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(ADVISORY_STAGE_MIN), MaxValueValidator(ADVISORY_STAGE_MAX)],
        verbose_name='Cantidad de etapas',
    )
    current_stage = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(ADVISORY_STAGE_MAX)],
        verbose_name='Etapa actual',
    )
    is_visible_portal = models.BooleanField(default=True, verbose_name='Visible en portal cliente')
    notes = models.TextField(blank=True, verbose_name='Notas internas')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{} — {}'.format(self.client_id, self.title)

    def save(self, *args, **kwargs):
        if self.current_stage > self.total_stages:
            self.current_stage = self.total_stages
        if self.current_stage < 1:
            self.current_stage = 1
        if self.total_stages < ADVISORY_STAGE_MIN:
            self.total_stages = ADVISORY_STAGE_MIN
        if self.total_stages > ADVISORY_STAGE_MAX:
            self.total_stages = ADVISORY_STAGE_MAX
        super().save(*args, **kwargs)
        if self.pk:
            sync_advisory_progress_stages(self)

    @staticmethod
    def build_predio_summary(client):
        if not client:
            return ''
        from core.pos.client_properties import client_property_to_dict, legacy_client_to_property_dict, property_summary_line
        props = list(client.properties.order_by('order', 'id'))
        if props:
            lines = [property_summary_line(client_property_to_dict(p)) for p in props]
            lines = [ln for ln in lines if ln]
            return ' | '.join(lines)[:500]
        if client.has_predio:
            return property_summary_line(legacy_client_to_property_dict(client))[:500]
        return ''

    def progress_percent(self):
        if self.total_stages <= 0:
            return 0
        return int(round(100.0 * self.current_stage / self.total_stages))

    def get_sale_json(self):
        if not self.sale_id:
            return None
        from core.pos.advisory_sale_cases import sale_advisory_json

        sale = self.sale
        if sale is None:
            sale = Sale.objects.filter(pk=self.sale_id).first()
        return sale_advisory_json(sale)

    def toJSON(self):
        stages = [s.toJSON() for s in self.stages.order_by('order')]
        return {
            'id': self.id,
            'client_id': self.client_id,
            'sale_id': self.sale_id,
            'title': self.title,
            'predio_summary': self.predio_summary or '',
            'total_stages': self.total_stages,
            'current_stage': self.current_stage,
            'progress_percent': self.progress_percent(),
            'is_visible_portal': self.is_visible_portal,
            'notes': self.notes or '',
            'stages': stages,
            'sale': self.get_sale_json(),
            'is_contract_case': bool(self.sale_id),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else '',
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else '',
        }

    class Meta:
        verbose_name = 'Control de avance asesoría'
        verbose_name_plural = 'Control de avance asesoría'
        default_permissions = ()
        permissions = (
            ('view_advisoryprogresscase', 'Can view Control de avance asesoría'),
            ('add_advisoryprogresscase', 'Can add Control de avance asesoría'),
            ('change_advisoryprogresscase', 'Can change Control de avance asesoría'),
            ('delete_advisoryprogresscase', 'Can delete Control de avance asesoría'),
        )
        ordering = ['-updated_at', '-id']


class AdvisoryProgressStage(models.Model):
    case = models.ForeignKey(
        AdvisoryProgressCase,
        on_delete=models.CASCADE,
        related_name='stages',
        verbose_name='Caso',
    )
    order = models.PositiveSmallIntegerField(verbose_name='Orden')
    title = models.CharField(max_length=150, verbose_name='Título de etapa')
    description = models.TextField(blank=True, verbose_name='Descripción')
    is_visible_portal = models.BooleanField(
        default=True,
        verbose_name='Visible en portal cliente',
    )

    def __str__(self):
        return '{} — {}'.format(self.order, self.title)

    def toJSON(self):
        return {
            'id': self.id,
            'order': self.order,
            'title': self.title,
            'description': self.description or '',
            'is_visible_portal': bool(self.is_visible_portal),
            'status': self.status_key(),
        }

    def status_key(self):
        case = self.case
        if self.order < case.current_stage:
            return 'done'
        if self.order == case.current_stage:
            return 'current'
        return 'pending'

    class Meta:
        verbose_name = 'Etapa de avance'
        verbose_name_plural = 'Etapas de avance'
        ordering = ['order']
        unique_together = (('case', 'order'),)


def sync_advisory_progress_stages(case, stage_titles=None):
    """Crea o ajusta las etapas según total_stages del caso."""
    total = max(ADVISORY_STAGE_MIN, min(ADVISORY_STAGE_MAX, int(case.total_stages or ADVISORY_STAGE_MIN)))
    titles = [t.strip() for t in (stage_titles or []) if t and str(t).strip()]
    existing = list(case.stages.order_by('order'))
    for i in range(1, total + 1):
        if i - 1 < len(titles):
            title = titles[i - 1]
        elif i - 1 < len(ADVISORY_DEFAULT_STAGE_TITLES):
            title = ADVISORY_DEFAULT_STAGE_TITLES[i - 1]
        else:
            title = 'Etapa {}'.format(i)
        if i <= len(existing):
            stage = existing[i - 1]
            if stage.order != i or stage.title != title:
                stage.order = i
                stage.title = title
                stage.save(update_fields=['order', 'title'])
        else:
            AdvisoryProgressStage.objects.create(
                case=case,
                order=i,
                title=title,
                is_visible_portal=True,
            )
    for stage in existing[total:]:
        stage.delete()


def portal_visible_stages(case):
    """Etapas que el cliente puede ver en el portal."""
    return list(case.stages.filter(is_visible_portal=True).order_by('order'))

