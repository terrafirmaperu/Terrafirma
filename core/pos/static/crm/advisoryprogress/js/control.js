/* global Swal */

const STAGE_MIN = window.ADVISORY_STAGE_MIN || 2;
const STAGE_MAX = window.ADVISORY_STAGE_MAX || 9;

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function getCsrfToken() {
    const fromInput = $('input[name="csrfmiddlewaretoken"]').val();
    if (fromInput) {
        return fromInput;
    }
    return getCookie('csrftoken');
}

function postUrl() {
    if (window.ADVISORY_CONTROL_URL) {
        return window.ADVISORY_CONTROL_URL;
    }
    if (typeof pathname !== 'undefined' && pathname) {
        return pathname;
    }
    return window.location.pathname;
}

function postAction(data) {
    const token = getCsrfToken();
    return $.ajax({
        url: postUrl(),
        type: 'POST',
        dataType: 'json',
        headers: {
            'X-CSRFToken': token,
            'X-Requested-With': 'XMLHttpRequest',
        },
        data: data,
    });
}

function ajaxErrorMessage(xhr, defaultMsg) {
    if (xhr.status === 403) {
        return 'Acceso denegado (CSRF o permisos). Recargue la página e intente de nuevo.';
    }
    if (xhr.status === 401) {
        return 'Sesión expirada. Vuelva a iniciar sesión en Qori.';
    }
    if (xhr.responseJSON && xhr.responseJSON.error) {
        return xhr.responseJSON.error;
    }
    if (xhr.status === 200 && xhr.responseText && xhr.responseText.indexOf('<!DOCTYPE') !== -1) {
        return 'La sesión expiró o la URL no es correcta. Recargue la página.';
    }
    return defaultMsg;
}

let currentClient = null;
let currentCases = [];
let searchTimer = null;

const DEFAULT_STAGE_TITLES = [
    'Recepción de expediente',
    'Estudio técnico y legal',
    'Saneamiento físico / topografía',
    'Elaboración de documentos',
    'Gestión municipal',
    'Presentación registral',
    'Seguimiento registral',
    'Inscripción registral',
    'Entrega de títulos',
];

function clampStages(n) {
    let v = parseInt(n, 10);
    if (isNaN(v)) {
        v = STAGE_MIN;
    }
    return Math.max(STAGE_MIN, Math.min(STAGE_MAX, v));
}

function getCurrentStage() {
    return clampStages($('#case_current_stage').val() || 1);
}

function setCurrentStage(n) {
    const v = clampStages(n);
    $('#case_current_stage').val(String(v));
    renderStagePicker();
    highlightStageEditorRow();
}

function escapeAttr(s) {
    return String(s || '')
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;');
}

function escapeHtml(s) {
    return String(s || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function renderStagePicker() {
    const total = clampStages($('#case_total_stages').val());
    const current = getCurrentStage();
    const $picker = $('#stage_picker');
    $picker.empty();
    for (let i = 1; i <= total; i++) {
        let cls = 'advisory-stage-pill';
        if (i < current) {
            cls += ' is-done';
        } else if (i === current) {
            cls += ' is-current';
        } else {
            cls += ' is-pending';
        }
        const $btn = $('<button type="button" class="' + cls + '" data-stage="' + i + '">Etapa ' + i + '</button>');
        $picker.append($btn);
    }
}

function highlightStageEditorRow() {
    const current = getCurrentStage();
    $('#stages_editor .stage-row').each(function () {
        const order = parseInt($(this).data('order'), 10);
        $(this).toggleClass('is-current-stage', order === current);
    });
}

function buildStagesEditor(total, stages) {
    const $ed = $('#stages_editor');
    $ed.empty();
    for (let i = 1; i <= total; i++) {
        const st = (stages || []).find(function (s) { return s.order === i; }) || {};
        const title = st.title || DEFAULT_STAGE_TITLES[i - 1] || ('Etapa ' + i);
        const desc = st.description || '';
        const visible = st.is_visible_portal !== false;
        const block =
            '<div class="mb-2 pb-2 border-bottom stage-row" data-order="' + i + '">' +
            '<div class="d-flex justify-content-between align-items-center mb-1">' +
            '<label class="small font-weight-bold mb-0">Etapa ' + i + '</label>' +
            '<div class="form-check form-check-inline mb-0">' +
            '<input type="checkbox" class="form-check-input stage-visible" id="stage-visible-' + i + '"' +
            (visible ? ' checked' : '') + '>' +
            '<label class="form-check-label small" for="stage-visible-' + i + '">Visible en portal</label>' +
            '</div></div>' +
            '<input type="text" class="form-control form-control-sm stage-title mb-1" value="' + escapeAttr(title) + '" maxlength="150">' +
            '<textarea class="form-control form-control-sm stage-desc" rows="2" placeholder="Descripción visible para el cliente">' + escapeHtml(desc) + '</textarea>' +
            '</div>';
        $ed.append(block);
    }
    highlightStageEditorRow();
}

function renderSalePanel(caseData) {
    const $panel = $('#case_sale_panel');
    const $meta = $('#case_sale_meta');
    if (!caseData || !caseData.sale) {
        $panel.addClass('d-none');
        $meta.empty();
        return;
    }
    const s = caseData.sale;
    $panel.removeClass('d-none');
    let html =
        '<div><code>' + escapeHtml(s.contract_code || '—') + '</code> · Venta <code>' +
        escapeHtml(s.sale_code || '—') + '</code></div>' +
        '<div>Fecha: ' + escapeHtml(s.date_joined_display || s.date_joined || '') +
        ' · Total: S/ ' + escapeHtml(s.total || '0.00') +
        ' · ' + escapeHtml(s.payment_condition_label || s.payment_condition || '') + '</div>';
    if (s.products_summary) {
        html += '<div class="mt-1"><strong>Servicios:</strong> ' + escapeHtml(s.products_summary) + '</div>';
    }
    if (s.details && s.details.length) {
        html += '<ul class="mb-0 pl-3 mt-1">';
        s.details.forEach(function (row) {
            html +=
                '<li>' + escapeHtml(row.product_name) +
                (row.cant > 1 ? ' (×' + row.cant + ')' : '') +
                ' — S/ ' + escapeHtml(row.total) + '</li>';
        });
        html += '</ul>';
    }
    $meta.html(html);
}

function renderCasesList() {
    const $list = $('#cases_list');
    $list.empty();
    if (!currentCases.length) {
        $list.append(
            '<li class="list-group-item text-muted">Sin contratas ni procesos. ' +
            'Si el cliente tiene ventas, vuelva a buscarlo para importarlas, o cree un caso manual.</li>'
        );
        return;
    }
    const sorted = currentCases.slice().sort(function (a, b) {
        const aSale = a.sale_id || (a.sale && a.sale.id) || 0;
        const bSale = b.sale_id || (b.sale && b.sale.id) || 0;
        if (aSale && !bSale) {
            return -1;
        }
        if (!aSale && bSale) {
            return 1;
        }
        return (b.id || 0) - (a.id || 0);
    });
    sorted.forEach(function (c) {
        const active = String($('#case_id').val()) === String(c.id) ? ' active' : '';
        const badge = 'Etapa ' + c.current_stage + ' / ' + c.total_stages;
        const isContract = !!(c.is_contract_case || c.sale_id || (c.sale && c.sale.id));
        const typeBadge = isContract
            ? '<span class="badge badge-primary advisory-case-type">Contrata</span>'
            : '<span class="badge badge-secondary advisory-case-type">Manual</span>';
        let contractLine = '';
        if (c.sale && c.sale.contract_code) {
            contractLine =
                '<div class="advisory-case-contract mb-1"><code class="h6 mb-0">' +
                escapeHtml(c.sale.contract_code) + '</code>' +
                (c.sale.sale_code ? ' <span class="text-muted small">· ' + escapeHtml(c.sale.sale_code) + '</span>' : '') +
                (c.sale.date_joined_display ? ' <span class="text-muted small">· ' +
                escapeHtml(c.sale.date_joined_display) + '</span>' : '') +
                '</div>';
        }
        let productsLine = '';
        if (c.sale && c.sale.products_summary) {
            productsLine = '<div class="small text-info">' + escapeHtml(c.sale.products_summary) + '</div>';
        }
        $list.append(
            '<li class="list-group-item list-group-item-action case-item' + active + '" data-id="' + c.id + '" style="cursor:pointer;">' +
            '<div class="d-flex justify-content-between align-items-start">' +
            '<div class="pr-2 flex-grow-1">' + typeBadge + contractLine +
            '<strong class="d-block">' + escapeHtml(c.title) + '</strong>' +
            '<div class="small text-muted">' + escapeHtml(c.predio_summary || '') + '</div>' +
            productsLine + '</div>' +
            '<span class="badge badge-info text-nowrap">' + badge + '</span></div></li>'
        );
    });
}

function showDniResults(clients, emptyMessage) {
    const $box = $('#dni_search_results');
    const $empty = $('#dni_search_empty');
    $box.empty();
    $empty.addClass('d-none').text('');
    if (!clients || !clients.length) {
        $box.addClass('d-none');
        if (emptyMessage) {
            $empty.text(emptyMessage).removeClass('d-none');
        }
        return;
    }
    clients.forEach(function (c) {
        const $item = $(
            '<button type="button" class="list-group-item list-group-item-action text-left dni-pick" data-id="' + c.id + '">' +
            '<strong>' + escapeHtml(c.full_name) + '</strong><br>' +
            '<span class="small">DNI: ' + escapeHtml(c.dni) + ' · Cód: <code>' + escapeHtml(c.client_code || '—') + '</code></span>' +
            '</button>'
        );
        $box.append($item);
    });
    $box.removeClass('d-none');
}

function applyClientPayload(res) {
    currentClient = res.client;
    currentCases = res.cases || [];
    $('#client_id').val(currentClient.id);
    const $sum = $('#client_summary');
    $sum.removeClass('d-none alert-danger').addClass('alert-secondary');
    $sum.html(
        '<strong>' + escapeHtml(currentClient.full_name) + '</strong><br>' +
        'DNI: ' + escapeHtml(currentClient.dni) +
        ' · Código: <code>' + escapeHtml(currentClient.client_code || '—') + '</code>'
    );
    $('#dni_search_results').addClass('d-none');
    $('#dni_search_empty').addClass('d-none');
    $('#cases_panel').removeClass('d-none');
    if (currentCases.length) {
        const firstContract = currentCases.find(function (c) {
            return c.is_contract_case || c.sale_id || (c.sale && c.sale.id);
        });
        loadCaseForm(firstContract || currentCases[0]);
    } else {
        loadCaseForm(null);
    }
    renderCasesList();
    if (res.message && typeof Swal !== 'undefined') {
        Swal.fire({ icon: 'info', title: 'Contratas', text: res.message, timer: 4500, showConfirmButton: true });
    }
}

function loadClientById(clientId) {
    $.LoadingOverlay('show');
    postAction({ action: 'load_client', client_id: clientId })
        .done(function (res) {
            if (res.error) {
                Swal.fire('Error', res.error, 'error');
                return;
            }
            applyClientPayload(res);
        })
        .fail(function (xhr) {
            Swal.fire('Error', ajaxErrorMessage(xhr, 'No se pudo cargar el cliente.'), 'error');
        })
        .always(function () {
            $.LoadingOverlay('hide');
        });
}

function searchClientsDebounced() {
    const dni = $('#search_dni').val().trim();
    const digits = dni.replace(/\D/g, '');
    if (digits.length < 2 && dni.length < 2) {
        $('#dni_search_results').addClass('d-none').empty();
        $('#dni_search_empty').addClass('d-none');
        return;
    }
    postAction({ action: 'search_clients', dni: dni })
        .done(function (res) {
            if (res.error) {
                showDniResults([], res.error);
                return;
            }
            const list = res.clients || [];
            if (!list.length) {
                showDniResults(
                    [],
                    res.message || 'Sin coincidencias. Verifique el DNI en Clientes o use más dígitos.'
                );
                return;
            }
            showDniResults(list);
        })
        .fail(function (xhr) {
            console.error('search_clients', xhr.status, xhr.responseText);
            showDniResults([], ajaxErrorMessage(xhr, 'Error al buscar. Recargue la página.'));
        });
}

function lookupClient() {
    const dni = $('#search_dni').val().trim();
    if (!dni) {
        Swal.fire('Aviso', 'Ingrese el DNI del cliente.', 'warning');
        return;
    }
    $.LoadingOverlay('show');
    postAction({ action: 'lookup_client', dni: dni })
        .done(function (res) {
            if (res.error && (!res.clients || !res.clients.length)) {
                showDniResults([], res.error);
                Swal.fire('Sin resultados', res.error, 'warning');
                return;
            }
            if (res.multiple && res.clients && res.clients.length) {
                showDniResults(res.clients, res.message);
                return;
            }
            if (res.client) {
                applyClientPayload(res);
                return;
            }
            showDniResults([], 'No se encontró el cliente.');
        })
        .fail(function (xhr) {
            console.error('lookup_client', xhr.status, xhr.responseText);
            const msg = ajaxErrorMessage(xhr, 'No se pudo buscar. Verifique su sesión en Qori.');
            showDniResults([], msg);
            Swal.fire('Error', msg, 'error');
        })
        .always(function () {
            $.LoadingOverlay('hide');
        });
}

function loadCaseForm(caseData) {
    if (!caseData) {
        $('#case_id').val('');
        $('#case_title').val('Saneamiento predial');
        $('#case_predio_summary').val(currentClient ? currentClient.predio_summary : '');
        $('#case_total_stages').val(5);
        setCurrentStage(1);
        $('#case_visible').prop('checked', true);
        $('#case_notes').val('');
        buildStagesEditor(5, []);
        renderStagePicker();
        renderSalePanel(null);
        $('#btn_delete_case').addClass('d-none');
        return;
    }
    $('#case_id').val(caseData.id);
    $('#case_title').val(caseData.title);
    $('#case_predio_summary').val(caseData.predio_summary);
    $('#case_total_stages').val(caseData.total_stages);
    setCurrentStage(caseData.current_stage);
    $('#case_visible').prop('checked', !!caseData.is_visible_portal);
    $('#case_notes').val(caseData.notes || '');
    buildStagesEditor(caseData.total_stages, caseData.stages || []);
    renderStagePicker();
    renderSalePanel(caseData);
    $('#btn_delete_case').removeClass('d-none');
}

function collectStagePayload() {
    const titles = [];
    const descriptions = [];
    const visibles = [];
    $('#stages_editor .stage-row').each(function () {
        titles.push($(this).find('.stage-title').val().trim());
        descriptions.push($(this).find('.stage-desc').val().trim());
        visibles.push($(this).find('.stage-visible').is(':checked'));
    });
    return { titles: titles, descriptions: descriptions, visibles: visibles };
}

function showSaveSuccess(res) {
    const portal = res.portal || {};
    let html = '<p class="text-left mb-2">' + escapeHtml(res.message || 'Avance actualizado.') + '</p>';
    if (portal.detail_url) {
        html += '<p class="text-left small mb-2">Vista del cliente (abra en otra pestaña; use DNI y código del cliente):</p>';
        html += '<p class="mb-0"><a href="' + escapeAttr(portal.detail_url) + '" target="_blank" rel="noopener" class="btn btn-sm btn-outline-primary">' +
            '<i class="fas fa-external-link-alt"></i> Ver avance en portal</a></p>';
    }
    if (portal.visible_stages_count === 0 || portal.case_visible === false) {
        html += '<p class="text-warning small text-left mt-2 mb-0"><strong>Aviso:</strong> revise los checkboxes de visibilidad antes de informar al cliente.</p>';
    }
    Swal.fire({
        icon: 'success',
        title: 'Guardado',
        html: html,
        confirmButtonText: 'Entendido',
    });
}

function saveCase() {
    if (!currentClient) {
        Swal.fire('Aviso', 'Primero busque y seleccione un cliente.', 'warning');
        return;
    }
    if (!$('#case_id').val() && !$('#case_title').val().trim()) {
        Swal.fire('Aviso', 'Indique el título del terreno / caso.', 'warning');
        return;
    }
    const total = clampStages($('#case_total_stages').val());
    const payload = collectStagePayload();
    const data = {
        action: 'save_case',
        client_id: currentClient.id,
        case_id: $('#case_id').val(),
        title: $('#case_title').val().trim(),
        predio_summary: $('#case_predio_summary').val().trim(),
        total_stages: total,
        current_stage: getCurrentStage(),
        is_visible_portal: $('#case_visible').is(':checked') ? 'true' : 'false',
        notes: $('#case_notes').val().trim(),
        stage_titles: JSON.stringify(payload.titles),
        stage_descriptions: JSON.stringify(payload.descriptions),
        stage_visibles: JSON.stringify(payload.visibles),
    };
    $.LoadingOverlay('show');
    postAction(data)
        .done(function (res) {
            if (res.error) {
                Swal.fire('Error', res.error, 'error');
                return;
            }
            const saved = res.case;
            const idx = currentCases.findIndex(function (c) { return c.id === saved.id; });
            if (idx >= 0) {
                currentCases[idx] = saved;
            } else {
                currentCases.push(saved);
            }
            loadCaseForm(saved);
            renderCasesList();
            showSaveSuccess(res);
        })
        .fail(function (xhr) {
            Swal.fire('Error', ajaxErrorMessage(xhr, 'No se pudo guardar. Verifique permisos y sesión.'), 'error');
        })
        .always(function () {
            $.LoadingOverlay('hide');
        });
}

function deleteCase() {
    const caseId = $('#case_id').val();
    if (!caseId) {
        return;
    }
    Swal.fire({
        title: '¿Eliminar este caso?',
        text: 'El cliente dejará de ver este terreno en el portal.',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar',
    }).then(function (result) {
        if (!result.isConfirmed) {
            return;
        }
        $.LoadingOverlay('show');
        postAction({ action: 'delete_case', case_id: caseId })
            .done(function (res) {
                if (res.error) {
                    Swal.fire('Error', res.error, 'error');
                    return;
                }
                currentCases = currentCases.filter(function (c) {
                    return String(c.id) !== String(caseId);
                });
                loadCaseForm(currentCases[0] || null);
                renderCasesList();
                Swal.fire('Eliminado', res.message, 'success');
            })
            .always(function () {
                $.LoadingOverlay('hide');
            });
    });
}

function onTotalStagesChange() {
    const total = clampStages($('#case_total_stages').val());
    $('#case_total_stages').val(total);
    let current = getCurrentStage();
    if (current > total) {
        current = total;
    }
    const payload = collectStagePayload();
    const stages = [];
    for (let i = 0; i < total; i++) {
        stages.push({
            order: i + 1,
            title: payload.titles[i] || '',
            description: payload.descriptions[i] || '',
            is_visible_portal: i < payload.visibles.length ? payload.visibles[i] !== false : true,
        });
    }
    buildStagesEditor(total, stages);
    setCurrentStage(current);
}

$(function () {
    $('#btn_lookup_dni').on('click', lookupClient);
    $('#search_dni').on('keypress', function (e) {
        if (e.which === 13) {
            e.preventDefault();
            lookupClient();
        }
    });
    $('#search_dni').on('input', function () {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(searchClientsDebounced, 350);
    });
    $('#dni_search_results').on('click', '.dni-pick', function () {
        loadClientById($(this).data('id'));
    });
    $('#case_total_stages').on('change input', onTotalStagesChange);
    $('#stage_picker').on('click', '.advisory-stage-pill', function () {
        setCurrentStage($(this).data('stage'));
    });
    $('#stages_editor').on('click', '.stage-row', function () {
        setCurrentStage($(this).data('order'));
    });
    $('#cases_list').on('click', '.case-item', function () {
        const id = parseInt($(this).data('id'), 10);
        const found = currentCases.find(function (c) { return c.id === id; });
        if (found) {
            loadCaseForm(found);
            renderCasesList();
        }
    });
    $('#btn_new_case').on('click', function () {
        loadCaseForm(null);
        renderCasesList();
    });
    $('#frmCase').on('submit', function (e) {
        e.preventDefault();
        saveCase();
    });
    $('#btn_delete_case').on('click', deleteCase);
    $('#case_total_stages').val(5);
    buildStagesEditor(5, []);
    setCurrentStage(1);
});
