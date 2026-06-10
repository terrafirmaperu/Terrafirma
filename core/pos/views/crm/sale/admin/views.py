import json
import os
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.http import JsonResponse
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, FormView
from weasyprint import HTML, CSS

from config import settings
from core.pos.client_properties import client_predios_template_context, save_client_properties_from_request
from core.pos.product_sale import active_promo_price_subquery, product_json_for_sale_row
from core.pos.dni_lookup import lookup_dni_data
from core.pos.forms import ClientForm, SaleForm
from core.pos.mixins import CashRegisterRequiredMixin
from core.pos.models import (
    CashRegisterSession,
    Client,
    Company,
    CtasCollect,
    PaymentsCtaCollect,
    Product,
    ClientProperty,
    Sale,
    SaleDetail,
)
from core.user.models import User
from core.reports.forms import ReportForm
from core.security.mixins import PermissionMixin, SupervisorDeleteApprovalMixin

_SALE_PRODUCT_SEARCH_LIMIT = 25


class SaleAdminListView(CashRegisterRequiredMixin, PermissionMixin, FormView):
    template_name = 'crm/sale/admin/list.html'
    permission_required = 'view_sale'
    form_class = ReportForm

    def post(self, request, *args, **kwargs):
        action = (request.POST.get('action') or '').strip()
        if not action:
            return JsonResponse({'error': 'Acción no indicada.'}, status=200)

        data = {}
        try:
            if action == 'search':
                data = []
                start_date = (request.POST.get('start_date') or '').strip()
                end_date = (request.POST.get('end_date') or '').strip()
                search = Sale.objects.select_related(
                    'client__user', 'employee', 'cash_register_session'
                ).order_by('-id')
                if start_date and end_date:
                    search = search.filter(date_joined__range=[start_date, end_date])
                for i in search:
                    data.append(i.toJSON())
            elif action == 'search_detproducts':
                sale_id = request.POST.get('id')
                if not sale_id:
                    data = {'error': 'Identificador de venta no indicado.'}
                else:
                    data = []
                    for det in SaleDetail.objects.filter(sale_id=sale_id).select_related(
                        'product__category'
                    ):
                        data.append(det.toJSON())
            else:
                data = {'error': 'No ha ingresado una opción'}
        except Exception as e:
            data = {'error': str(e)}

        if isinstance(data, list):
            return JsonResponse(data, safe=False)
        return JsonResponse(data, status=200)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create_url'] = reverse_lazy('sale_admin_create')
        context['title'] = 'Listado de Ventas'
        return context


class SaleAdminCreateView(CashRegisterRequiredMixin, PermissionMixin, CreateView):
    model = Sale
    template_name = 'crm/sale/admin/create.html'
    form_class = SaleForm
    success_url = reverse_lazy('sale_admin_list')
    permission_required = 'add_sale'

    def validate_client(self):
        data = {'valid': True}
        try:
            type = self.request.POST['type']
            obj = self.request.POST['obj'].strip()
            client_id = self.request.POST.get('client_id') or self.request.POST.get('existing_client_id') or None
            if type == 'dni':
                qs = User.objects.filter(dni=obj)
                if client_id:
                    qs = qs.exclude(client__id=client_id)
                if qs.exists():
                    data['valid'] = False
            elif type == 'mobile':
                qs = Client.objects.filter(mobile=obj)
                if client_id:
                    qs = qs.exclude(pk=client_id)
                if qs.exists():
                    data['valid'] = False
            elif type == 'email':
                qs = User.objects.filter(email__iexact=obj)
                if client_id:
                    qs = qs.exclude(client__id=client_id)
                if obj and qs.exists():
                    data['valid'] = False
        except:
            pass
        return JsonResponse(data)

    def get_form(self, form_class=None):
        form = SaleForm()
        client = Client.objects.filter(user__dni='9999999999')
        if client.exists():
            form.initial = {'client': client[0]}
        return form

    def post(self, request, *args, **kwargs):
        action = request.POST['action']
        data = {}
        try:
            if action == 'add':
                client_id = int(request.POST['client'])
                products_payload = json.loads(request.POST.get('products') or '[]')
                from core.pos.client_properties import validate_sale_products_not_duplicated

                dup_error = validate_sale_products_not_duplicated(client_id, products_payload)
                if dup_error:
                    data['error'] = dup_error
                    return HttpResponse(json.dumps(data), content_type='application/json')

                with transaction.atomic():
                    sale = Sale()
                    sale.employee_id = request.user.id
                    sale.client_id = client_id
                    sale.payment_method = request.POST['payment_method']
                    sale.payment_condition = request.POST['payment_condition']
                    sale.type_voucher = request.POST['type_voucher']
                    sale.cash_register_session = CashRegisterSession.get_open_session()
                    company = Company.objects.first()
                    sale.igv = float(company.igv) / 100 if company else 0.0
                    sale.dscto = float(request.POST['dscto']) / 100
                    sale.save()

                    for i in json.loads(request.POST['products']):
                        prod = Product.objects.get(pk=i['id'])
                        saledetail = SaleDetail()
                        saledetail.sale_id = sale.id
                        saledetail.product_id = prod.id
                        raw_prop = i.get('client_property_id')
                        if raw_prop not in (None, '', 0, '0'):
                            try:
                                saledetail.client_property_id = int(raw_prop)
                            except (TypeError, ValueError):
                                saledetail.client_property_id = None
                        saledetail.price = float(i['price_current'])
                        saledetail.cant = int(i['cant'])
                        saledetail.subtotal = saledetail.price * saledetail.cant
                        saledetail.dscto = float(i['dscto']) / 100
                        saledetail.total_dscto = saledetail.dscto * saledetail.subtotal
                        saledetail.total = saledetail.subtotal - saledetail.total_dscto
                        saledetail.save()

                    sale.calculate_invoice()

                    if sale.payment_condition == 'credito':
                        sale.payment_method = 'efectivo'
                        try:
                            quota_count = int(request.POST.get('credit_quota_count', '1'))
                        except (ValueError, TypeError):
                            quota_count = 1
                        quota_count = max(1, min(60, quota_count))
                        sale_joined = sale.date_joined
                        sale_date = sale_joined.date() if hasattr(sale_joined, 'date') else sale_joined
                        custom_end_credit = (request.POST.get('custom_end_credit_enabled') or '').strip() in (
                            '1', 'true', 'on', 'yes'
                        )
                        if custom_end_credit:
                            end_credit_raw = (request.POST.get('end_credit') or '').strip()
                            try:
                                end_credit = datetime.strptime(end_credit_raw, '%Y-%m-%d').date()
                            except ValueError:
                                raise ValueError('La fecha límite de crédito no es válida.')
                            diff_days = (end_credit - sale_date).days
                            if diff_days <= 0:
                                raise ValueError('La fecha límite debe ser posterior a la fecha de venta.')
                            if diff_days == 1:
                                raise ValueError('El plazo de crédito no puede ser de 1 solo día.')
                            if diff_days < quota_count:
                                raise ValueError(
                                    f'Para {quota_count} cuota(s), el plazo debe ser al menos de {quota_count} día(s).'
                                )
                        else:
                            end_credit = sale_date + timedelta(days=25 * quota_count)
                        sale.end_credit = end_credit
                        try:
                            inicial = Decimal(
                                str(request.POST.get('credit_down_payment', '0') or '0').replace(',', '.')
                            )
                        except Exception:
                            inicial = Decimal('0')
                        total_amt = Decimal(str(sale.total))
                        inicial = inicial.quantize(Decimal('0.01'))
                        if inicial < 0:
                            raise ValueError('La inicial no puede ser negativa.')
                        if inicial >= total_amt:
                            raise ValueError('La inicial debe ser menor que el total a pagar.')
                        method_ini = (request.POST.get('credit_down_payment_method') or 'efectivo').strip()
                        if method_ini not in ('efectivo', 'yape', 'plin', 'tarjeta_debito_credito'):
                            method_ini = 'efectivo'
                        sale.credit_quota_count = quota_count
                        sale.credit_down_payment = inicial
                        sale.credit_down_payment_method = method_ini if inicial > 0 else 'efectivo'
                        if inicial > 0 and method_ini == 'efectivo':
                            sale.cash = float(inicial)
                            sale.change = 0.00
                        elif inicial > 0 and method_ini == 'tarjeta_debito_credito':
                            sale.cash = 0.00
                            sale.change = 0.00
                            try:
                                amt_card = Decimal(
                                    str(request.POST.get('amount_debited', '0') or '0').replace(',', '.')
                                ).quantize(Decimal('0.01'))
                            except Exception:
                                amt_card = Decimal('0')
                            if amt_card != inicial:
                                raise ValueError(
                                    'El monto a debitar en tarjeta debe ser igual a la inicial.'
                                )
                            sale.card_number = (request.POST.get('card_number') or '').strip()
                            sale.titular = (request.POST.get('titular') or '').strip()
                            sale.amount_debited = float(amt_card)
                        else:
                            sale.cash = 0.00
                            sale.change = 0.00
                        sale.save()
                        ctascollect = CtasCollect()
                        ctascollect.sale_id = sale.id
                        ctascollect.date_joined = sale.date_joined
                        ctascollect.end_date = sale.end_credit
                        ctascollect.debt = total_amt
                        ctascollect.saldo = total_amt
                        ctascollect.save()
                        if inicial > 0:
                            pay_ini = PaymentsCtaCollect()
                            pay_ini.ctascollect_id = ctascollect.id
                            pay_ini.cash_register_session_id = sale.cash_register_session_id
                            pay_ini.date_joined = sale.date_joined
                            labels = {
                                'efectivo': 'Efectivo',
                                'yape': 'Yape',
                                'plin': 'Plin',
                                'tarjeta_debito_credito': 'Tarjeta',
                            }
                            pay_ini.payment_method = method_ini
                            pay_ini.desc = (
                                'Cuota inicial ({}) — {} cuota(s) programada(s)'.format(
                                    labels.get(method_ini, method_ini),
                                    quota_count,
                                )
                            )
                            pay_ini.valor = float(inicial)
                            pay_ini.save()
                            ctascollect.validate_debt()
                    elif sale.payment_condition == 'contado':
                        sale.credit_quota_count = 1
                        sale.credit_down_payment = Decimal('0.00')
                        sale.credit_down_payment_method = 'efectivo'
                        if sale.payment_method == 'efectivo':
                            sale.cash = float(request.POST['cash'])
                            sale.change = float(sale.cash) - sale.total
                            sale.save()
                        elif sale.payment_method in ['yape', 'plin']:
                            sale.cash = 0.00
                            sale.change = 0.00
                            sale.save()
                        elif sale.payment_method == 'tarjeta_debito_credito':
                            sale.card_number = request.POST['card_number']
                            sale.titular = request.POST['titular']
                            sale.amount_debited = float(request.POST['amount_debited'])
                            sale.save()
                        elif sale.payment_method == 'efectivo_tarjeta':
                            sale.cash = float(request.POST['cash'])
                            sale.change = float(request.POST.get('change', 0) or 0)
                            sale.card_number = request.POST['card_number']
                            sale.titular = request.POST['titular']
                            sale.amount_debited = float(request.POST['amount_debited'])
                            sale.save()

                    sale.refresh_from_db()
                    from core.pos.advisory_sale_cases import ensure_advisory_case_for_sale

                    ensure_advisory_case_for_sale(sale)
                    data = {
                        'id': sale.id,
                        'sale_code': sale.sale_code or '',
                        'contract_code': sale.contract_code or '',
                        'contract_docx_basename': sale.contract_docx_basename(),
                        'payment_condition': sale.payment_condition,
                    }
            elif action == 'validate_sale_products':
                try:
                    client_id = int(request.POST.get('client_id', 0))
                except (TypeError, ValueError):
                    client_id = 0
                try:
                    products_payload = json.loads(request.POST.get('products') or '[]')
                except json.JSONDecodeError:
                    products_payload = []
                from core.pos.client_properties import (
                    find_duplicate_predio_sales,
                    format_duplicate_predio_sale_error,
                )

                duplicates = find_duplicate_predio_sales(client_id, products_payload)
                if duplicates:
                    data['error'] = format_duplicate_predio_sale_error(duplicates)
                    data['duplicates'] = duplicates
                else:
                    data['ok'] = True
            elif action == 'search_products':
                ids = json.loads(request.POST.get('ids') or '[]')
                term = (request.POST.get('term') or '').strip()
                qs = (
                    Product.objects.exclude(id__in=ids)
                    .select_related('category')
                    .annotate(_promo_final=active_promo_price_subquery())
                    .only(
                        'id',
                        'name',
                        'price',
                        'pvp',
                        'image',
                        'category_id',
                        'category__id',
                        'category__name',
                    )
                )
                if term:
                    qs = qs.filter(
                        Q(name__icontains=term) | Q(category__name__icontains=term)
                    ).order_by('name')
                else:
                    qs = qs.order_by('-id')
                data = [
                    product_json_for_sale_row(p)
                    for p in qs[:_SALE_PRODUCT_SEARCH_LIMIT]
                ]
            elif action == 'search_client':
                data = []
                term = request.POST['term']
                for p in (
                    Client.objects.filter(
                        Q(user__first_name__icontains=term)
                        | Q(user__last_name__icontains=term)
                        | Q(user__dni__icontains=term)
                    )
                    .select_related('user')
                    .prefetch_related(
                        Prefetch(
                            'properties',
                            queryset=ClientProperty.objects.select_related(
                                'product', 'product__category',
                            ).order_by('order', 'id'),
                        ),
                    )
                    .order_by('user__first_name')[:10]
                ):
                    item = p.toJSON()
                    item['text'] = '{} / {}'.format(p.user.get_full_name(), p.user.dni)
                    data.append(item)
            elif action == 'validate_client':
                return self.validate_client()
            elif action == 'lookup_dni':
                dni = (request.POST.get('dni') or '').strip()
                existing_client = (
                    Client.objects.filter(user__dni=dni)
                    .select_related('user')
                    .prefetch_related(
                        Prefetch(
                            'properties',
                            queryset=ClientProperty.objects.select_related(
                                'product', 'product__category',
                            ).order_by('order', 'id'),
                        ),
                    )
                    .first()
                )
                if existing_client:
                    item = existing_client.toJSON()
                    item['text'] = '{} / {}'.format(
                        existing_client.user.get_full_name(),
                        existing_client.user.dni,
                    )
                    return JsonResponse({
                        'success': True,
                        'existing_client': True,
                        'client': item,
                    })
                payload = lookup_dni_data(dni)
                if payload.get('error'):
                    return JsonResponse({'success': False, 'error': payload['error']})
                return JsonResponse({'success': True, 'data': payload})
            elif action == 'create_client':
                with transaction.atomic():
                    existing_client_id = request.POST.get('existing_client_id') or ''
                    if existing_client_id:
                        client = (
                            Client.objects.select_for_update()
                            .select_related('user')
                            .get(pk=int(existing_client_id))
                        )
                        user = client.user
                        dni = (request.POST.get('dni') or '').strip()
                        if dni and user.dni != dni and User.objects.filter(dni=dni).exclude(pk=user.pk).exists():
                            data['error'] = 'El número de Dni o cédula ya se encuentra registrado'
                            return HttpResponse(json.dumps(data), content_type='application/json')
                    else:
                        user = User()
                        user.dni = request.POST['dni']
                        user.username = user.dni
                        user.create_or_update_password(user.dni)
                        client = Client()

                    user.first_name = request.POST['first_name']
                    user.last_name = request.POST['last_name']
                    user.dni = request.POST['dni']
                    if not user.username:
                        user.username = user.dni
                    user.email = (request.POST.get('email') or '').strip()
                    user.save()

                    client.user_id = user.id
                    client.mobile = request.POST['mobile']
                    client.department = (request.POST.get('department') or '').strip()
                    client.province = (request.POST.get('province') or '').strip()
                    client.district = (request.POST.get('district') or '').strip()
                    client.address = request.POST['address']
                    client.save()
                    try:
                        save_client_properties_from_request(
                            request,
                            client,
                            request.POST.get('properties_json', '[]'),
                        )
                    except ValueError as exc:
                        data['error'] = str(exc)
                        return HttpResponse(json.dumps(data), content_type='application/json')

                    if not existing_client_id:
                        group = Group.objects.get(pk=settings.GROUPS.get('client'))
                        user.groups.add(group)

                    data = (
                        Client.objects.prefetch_related('properties')
                        .select_related('user')
                        .get(pk=client.id)
                        .toJSON()
                    )
                    data['text'] = '{} / {}'.format(client.user.get_full_name(), client.user.dni)
            elif action == 'create_proforma':
                ventsjson = json.loads(request.POST['vents'])
                template = get_template('crm/sale/print/proforma.html')
                html_template = template.render({'sale': ventsjson, 'company': Company.objects.first() or {}}).encode(
                    encoding="UTF-8")
                url_css = os.path.join(settings.BASE_DIR, 'static/lib/bootstrap-4.6.0/css/bootstrap.min.css')
                pdf_file = HTML(string=html_template, base_url=request.build_absolute_uri()).write_pdf(
                    stylesheets=[CSS(url_css)], presentational_hints=True)
                response = HttpResponse(pdf_file, content_type='application/pdf')
                return response
            else:
                data['error'] = 'No ha ingresado una opción'
        except Exception as e:
            data['error'] = str(e)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['frmClient'] = ClientForm()
        context.update(client_predios_template_context())
        context['list_url'] = self.success_url
        context['title'] = 'Nuevo registro de una Venta'
        context['action'] = 'add'
        company = Company.objects.first()
        context['igv'] = company.get_igv() if company else '0.00'
        return context


class SaleAdminDeleteView(SupervisorDeleteApprovalMixin, CashRegisterRequiredMixin, PermissionMixin, DeleteView):
    model = Sale
    template_name = 'crm/sale/admin/delete.html'
    success_url = reverse_lazy('sale_admin_list')
    permission_required = 'delete_sale'

    def post(self, request, *args, **kwargs):
        from core.pos.sale_annulment import SaleAlreadyVoidedError, annul_sale

        data = {}
        try:
            sale = self.get_object()
            annul_sale(sale, user=request.user)
            data['message'] = 'Venta anulada correctamente.'
        except SaleAlreadyVoidedError as exc:
            data['error'] = str(exc)
        except Exception as exc:
            data['error'] = str(exc)
        return HttpResponse(json.dumps(data), content_type='application/json')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sale = context.get('object')
        if sale and sale.is_voided:
            context['title'] = 'Venta ya anulada'
            context['already_voided'] = True
        else:
            context['title'] = 'Anular venta'
            context['already_voided'] = False
        context['list_url'] = self.success_url
        return context
