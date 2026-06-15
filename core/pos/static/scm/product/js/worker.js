/* global Swal */

let deliverables = [];
let suggestedStages = [];

function getCsrfToken() {
    const fromInput = $('input[name="csrfmiddlewaretoken"]').val();
    if (fromInput) {
        return fromInput;
    }
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, 10) === 'csrftoken=') {
                cookieValue = decodeURIComponent(cookie.substring(10));
                break;
            }
        }
    }
    return cookieValue;
}

function postWorker(data) {
    return $.ajax({
        url: window.PRODUCT_WORKER_URL,
        type: 'POST',
        dataType: 'json',
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest',
        },
        data: data,
    });
}

function escapeAttr(s) {
    return String(s || '')
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;');
}

function parseMoney(val) {
    const n = parseFloat(String(val || '0').replace(',', '.'));
    return isNaN(n) ? 0 : n;
}

function formatMoney(n) {
    return 'S/ ' + parseMoney(n).toFixed(2);
}

function recalcTotals() {
    const inscription = parseMoney($('#inscription_amount').val());
    let delSubtotal = 0;
    $('#deliverables_body tr').each(function () {
        delSubtotal += parseMoney($(this).find('.del-charge').val());
    });
    const totalGeneral = inscription + delSubtotal;

    $('#inscription_total_display').text(formatMoney(inscription));
    $('#deliverables_subtotal_display').text(formatMoney(delSubtotal));
    $('#deliverables_total_display').text(formatMoney(totalGeneral));
}

function renderDeliverables() {
    const $body = $('#deliverables_body');
    $body.empty();
    deliverables.forEach(function (row, idx) {
        const tr =
            '<tr data-idx="' + idx + '">' +
            '<td class="text-center align-middle">' + (idx + 1) + '</td>' +
            '<td class="col-name"><input type="text" class="form-control form-control-sm del-name" ' +
            'value="' + escapeAttr(row.name) + '" maxlength="200" placeholder="Nombre del proceso"></td>' +
            '<td><input type="number" class="form-control form-control-sm del-charge" min="0" step="0.01" ' +
            'value="' + escapeAttr(row.charge_amount || '0.00') + '"></td>' +
            '<td><input type="text" class="form-control form-control-sm del-notes" ' +
            'value="' + escapeAttr(row.notes) + '" maxlength="300" placeholder="Opcional"></td>' +
            '<td class="text-center align-middle">' +
            '<button type="button" class="btn btn-danger btn-xs btn-flat btn-remove-del" title="Quitar">' +
            '<i class="fas fa-times"></i></button></td></tr>';
        $body.append(tr);
        if (row.id) {
            $body.find('tr').last().data('id', row.id);
        }
    });
    recalcTotals();
}

function collectDeliverablesFromDom() {
    const rows = [];
    $('#deliverables_body tr').each(function () {
        const name = $(this).find('.del-name').val().trim();
        if (!name) {
            return;
        }
        rows.push({
            id: $(this).data('id') || null,
            name: name,
            charge_amount: parseMoney($(this).find('.del-charge').val()).toFixed(2),
            notes: $(this).find('.del-notes').val().trim(),
        });
    });
    return rows;
}

function loadConfig() {
    $.LoadingOverlay('show');
    postWorker({ action: 'load' })
        .done(function (res) {
            suggestedStages = res.suggested_stages || [];
            const cfg = res.config || {};
            $('#inscription_amount').val(cfg.inscription_amount || '0.00');
            deliverables = res.deliverables || [];
            renderDeliverables();
        })
        .fail(function (xhr) {
            const msg = (xhr.responseJSON && xhr.responseJSON.error) || 'No se pudo cargar la configuración.';
            Swal.fire('Error', msg, 'error');
        })
        .always(function () {
            $.LoadingOverlay('hide');
        });
}

function saveConfig() {
    const rows = collectDeliverablesFromDom();
    const data = {
        action: 'save',
        inscription_amount: $('#inscription_amount').val(),
        deliverables: JSON.stringify(rows),
    };
    $.LoadingOverlay('show');
    postWorker(data)
        .done(function (res) {
            if (res.error) {
                Swal.fire('Error', res.error, 'error');
                return;
            }
            deliverables = res.deliverables || [];
            renderDeliverables();
            Swal.fire('Guardado', res.message || 'Configuración actualizada.', 'success');
        })
        .fail(function (xhr) {
            const msg = (xhr.responseJSON && xhr.responseJSON.error) || 'No se pudo guardar.';
            Swal.fire('Error', msg, 'error');
        })
        .always(function () {
            $.LoadingOverlay('hide');
        });
}

function addEmptyRow() {
    deliverables = collectDeliverablesFromDom();
    deliverables.push({ name: '', charge_amount: '0.00', notes: '' });
    renderDeliverables();
    const $last = $('#deliverables_body tr').last();
    $last.find('.del-name').focus();
}

function loadSuggestedStages() {
    if (!suggestedStages.length) {
        Swal.fire('Aviso', 'No hay etapas sugeridas disponibles.', 'info');
        return;
    }
    Swal.fire({
        title: '¿Cargar etapas sugeridas?',
        text: 'Se reemplazarán las filas actuales por las etapas estándar de asesoría.',
        icon: 'question',
        showCancelButton: true,
        confirmButtonText: 'Sí, cargar',
        cancelButtonText: 'Cancelar',
    }).then(function (result) {
        if (!result.isConfirmed) {
            return;
        }
        deliverables = suggestedStages.map(function (title) {
            return { name: title, charge_amount: '0.00', notes: '' };
        });
        renderDeliverables();
    });
}

$(function () {
    loadConfig();

    $('#inscription_amount').on('input change', recalcTotals);
    $('#deliverables_body').on('input change', '.del-charge', recalcTotals);

    $('#btn_add_deliverable').on('click', addEmptyRow);
    $('#btn_load_suggested').on('click', loadSuggestedStages);
    $('#btn_save_worker').on('click', saveConfig);

    $('#deliverables_body').on('click', '.btn-remove-del', function () {
        $(this).closest('tr').remove();
        deliverables = collectDeliverablesFromDom();
        renderDeliverables();
    });
});
