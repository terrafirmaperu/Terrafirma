import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse, reverse_lazy
from config import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

from core.pos.advisory_dni import (
    ADVISORY_STAGE_MAX,
    ADVISORY_STAGE_MIN,
    DNI_SEARCH_MIN_LEN,
    clamp_stage_count,
    client_to_lookup_dict,
    find_client_by_dni_exact,
    find_clients_by_dni,
    normalize_dni,
)
from core.pos.advisory_sale_cases import sync_advisory_cases_for_client
from core.pos.models import (
    AdvisoryProgressCase,
    sync_advisory_progress_stages,
)
from core.security.mixins import PermissionMixin


@method_decorator(ensure_csrf_cookie, name='dispatch')
@method_decorator(login_required, name='dispatch')
class AdvisoryProgressControlView(PermissionMixin, TemplateView):
    """Control de avance de asesoría por cliente (búsqueda DNI)."""

    template_name = 'crm/advisoryprogress/control.html'
    permission_required = 'view_advisoryprogresscase'

    def _group_has_perm(self, codename):
        """Permisos del grupo en sesión (no confundir con permission_required del módulo)."""
        from core.security.session_group import get_group_from_session
        group = get_group_from_session(self.request)
        if not group:
            return False
        return group.grouppermission_set.filter(permission__codename=codename).exists()

    def _can_change(self):
        return (
            self._group_has_perm('change_advisoryprogresscase')
            or self._group_has_perm('add_advisoryprogresscase')
        )

    def _can_delete(self):
        return self._group_has_perm('delete_advisoryprogresscase')

    def get(self, request, *args, **kwargs):
        """PermissionMixin.get puede devolver None si falta grupo en sesión."""
        if 'group' not in request.session:
            messages.error(
                request,
                'Debe elegir su grupo de trabajo en el panel antes de usar este módulo.',
            )
            return HttpResponseRedirect(reverse('dashboard'))
        response = super().get(request, *args, **kwargs)
        if response is None:
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
        return response

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST' and self._is_ajax(request):
            if not request.user.is_authenticated:
                return JsonResponse(
                    {'error': 'Sesión expirada. Vuelva a iniciar sesión en Qori.'},
                    status=401,
                )
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _is_ajax(request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return True
        accept = request.headers.get('Accept') or ''
        return 'application/json' in accept

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', '')
        try:
            if action == 'search_clients':
                return self._search_clients(request)
            if action == 'lookup_client':
                return self._lookup_client(request)
            if action == 'load_client':
                return self._load_client(request)
            if action == 'save_case':
                if not self._can_change():
                    return JsonResponse({'error': 'Sin permiso para guardar.'}, status=403)
                return self._save_case(request)
            if action == 'delete_case':
                if not self._can_delete():
                    return JsonResponse({'error': 'Sin permiso para eliminar.'}, status=403)
                return self._delete_case(request)
            return JsonResponse({'error': 'Acción no válida'})
        except Exception as exc:
            return JsonResponse({'error': str(exc)})

    def _search_clients(self, request):
        dni = (request.POST.get('dni') or '').strip()
        digits = normalize_dni(dni)
        if len(digits) < DNI_SEARCH_MIN_LEN and len(dni) < DNI_SEARCH_MIN_LEN:
            return JsonResponse({
                'clients': [],
                'count': 0,
                'message': 'Escriba al menos {} caracteres del DNI o código.'.format(DNI_SEARCH_MIN_LEN),
            })
        clients = find_clients_by_dni(dni, limit=20)
        return JsonResponse({
            'clients': [client_to_lookup_dict(c) for c in clients],
            'count': len(clients),
        })

    def _lookup_client(self, request):
        dni = (request.POST.get('dni') or '').strip()
        if not dni:
            return JsonResponse({'error': 'Ingrese un DNI.'})
        clients = list(find_clients_by_dni(dni, limit=20))
        if not clients:
            return JsonResponse({
                'error': (
                    'No hay cliente con ese DNI o código. Regístrelo en Clientes (CRM) '
                    'o busque con los primeros dígitos del documento (mín. {}).'
                ).format(DNI_SEARCH_MIN_LEN),
                'clients': [],
                'count': 0,
            })
        client = find_client_by_dni_exact(dni)
        if client is None and len(clients) > 1:
            return JsonResponse({
                'multiple': True,
                'clients': [client_to_lookup_dict(c) for c in clients],
                'message': 'Varios clientes coinciden. Elija uno de la lista.',
            })
        client = client or clients[0]
        return self._client_payload(client)

    def _load_client(self, request):
        try:
            client_id = int(request.POST.get('client_id', 0))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Cliente no válido.'})
        from core.pos.models import Client

        client = Client.objects.select_related('user').filter(pk=client_id).first()
        if not client:
            return JsonResponse({'error': 'Cliente no encontrado.'})
        return self._client_payload(client)

    def _client_payload(self, client):
        synced = sync_advisory_cases_for_client(client)
        cases = (
            AdvisoryProgressCase.objects.filter(client=client)
            .select_related('sale')
            .prefetch_related('stages', 'sale__saledetail_set__product')
            .order_by('-sale_id', '-updated_at', '-id')
        )
        case_list = [c.toJSON() for c in cases]
        payload = {
            'client': client_to_lookup_dict(client),
            'cases': case_list,
        }
        if synced:
            payload['message'] = (
                'Se importaron {} contrata(s) desde ventas. '
                'Seleccione cada una para registrar su etapa.'
            ).format(synced)
        return JsonResponse(payload)

    def _save_case(self, request):
        client_id = request.POST.get('client_id')
        case_id = request.POST.get('case_id')
        if not client_id:
            return JsonResponse({'error': 'Cliente no indicado.'})
        from core.pos.models import Client

        client = Client.objects.filter(pk=client_id).first()
        if not client:
            return JsonResponse({'error': 'Cliente no encontrado.'})

        title = (request.POST.get('title') or '').strip() or 'Saneamiento predial'
        total_stages = clamp_stage_count(request.POST.get('total_stages'))
        try:
            current_stage = int(request.POST.get('current_stage') or 1)
        except (TypeError, ValueError):
            current_stage = 1
        current_stage = max(ADVISORY_STAGE_MIN, min(total_stages, current_stage))

        predio_summary = (request.POST.get('predio_summary') or '').strip()
        if not predio_summary:
            predio_summary = AdvisoryProgressCase.build_predio_summary(client)

        notes = (request.POST.get('notes') or '').strip()
        is_visible = request.POST.get('is_visible_portal', 'true').lower() in ('1', 'true', 'on', 'yes')

        stage_titles_raw = request.POST.get('stage_titles', '[]')
        try:
            stage_titles = json.loads(stage_titles_raw) if stage_titles_raw else []
        except json.JSONDecodeError:
            stage_titles = []
        if not isinstance(stage_titles, list):
            stage_titles = []

        stage_descriptions_raw = request.POST.get('stage_descriptions', '[]')
        try:
            stage_descriptions = json.loads(stage_descriptions_raw) if stage_descriptions_raw else []
        except json.JSONDecodeError:
            stage_descriptions = []
        if not isinstance(stage_descriptions, list):
            stage_descriptions = []

        stage_visibles_raw = request.POST.get('stage_visibles', '[]')
        try:
            stage_visibles = json.loads(stage_visibles_raw) if stage_visibles_raw else []
        except json.JSONDecodeError:
            stage_visibles = []
        if not isinstance(stage_visibles, list):
            stage_visibles = []

        with transaction.atomic():
            if case_id:
                case = AdvisoryProgressCase.objects.filter(pk=case_id, client=client).first()
                if not case:
                    return JsonResponse({'error': 'Caso no encontrado.'})
            else:
                case = AdvisoryProgressCase(client=client)

            case.title = title
            case.predio_summary = predio_summary
            case.total_stages = total_stages
            case.current_stage = current_stage
            case.notes = notes
            case.is_visible_portal = is_visible
            case.save()
            sync_advisory_progress_stages(case, stage_titles)

            for stage in case.stages.order_by('order'):
                idx = stage.order - 1
                update_fields = []
                if idx < len(stage_descriptions):
                    desc = (stage_descriptions[idx] or '').strip()
                    if stage.description != desc:
                        stage.description = desc
                        update_fields.append('description')
                if idx < len(stage_visibles):
                    visible = stage_visibles[idx]
                    if isinstance(visible, str):
                        visible = visible.lower() in ('1', 'true', 'on', 'yes')
                    else:
                        visible = bool(visible)
                    if stage.is_visible_portal != visible:
                        stage.is_visible_portal = visible
                        update_fields.append('is_visible_portal')
                if update_fields:
                    stage.save(update_fields=update_fields)

        case = (
            AdvisoryProgressCase.objects.filter(pk=case.pk)
            .prefetch_related('stages', 'sale__saledetail_set__product')
            .first()
        )
        visible_count = case.stages.filter(is_visible_portal=True).count()
        portal_detail_url = reverse('cliente_avance_detalle', args=[case.pk])
        portal_login_url = reverse('cliente_login')

        hints = []
        if not case.is_visible_portal:
            hints.append(
                'El caso no está marcado como «Visible en portal cliente»; el cliente no verá esta contrata.'
            )
        if visible_count == 0:
            hints.append(
                'Ninguna etapa tiene «Visible en portal» activado; el cliente verá el caso vacío.'
            )

        message = 'Avance guardado correctamente.'
        if hints:
            message += ' ' + ' '.join(hints)

        return JsonResponse({
            'message': message,
            'case': case.toJSON(),
            'portal': {
                'login_url': portal_login_url,
                'detail_url': portal_detail_url,
                'case_visible': case.is_visible_portal,
                'visible_stages_count': visible_count,
            },
        })

    def _delete_case(self, request):
        case_id = request.POST.get('case_id')
        deleted, _ = AdvisoryProgressCase.objects.filter(pk=case_id).delete()
        if not deleted:
            return JsonResponse({'error': 'Caso no encontrado.'})
        return JsonResponse({'message': 'Caso eliminado.'})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = 'Control de Avance Asesoría'
        ctx['list_url'] = reverse_lazy('advisory_progress_control')
        ctx['control_url'] = reverse('advisory_progress_control')
        ctx['can_change'] = self._can_change()
        ctx['can_delete'] = self._can_delete()
        ctx['stage_min'] = ADVISORY_STAGE_MIN
        ctx['stage_max'] = ADVISORY_STAGE_MAX
        return ctx
