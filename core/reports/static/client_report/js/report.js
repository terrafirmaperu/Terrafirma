var tblReport;
var tblPaidToday;
var tblDebtors;
var tblPaymentsByDay;
var tblCancellations;
var tblEnrollmentSummary;
var tblProductEnrollmentSummary;
var tblProductDebtorsDetail;
var tblProductQuotaPayments;
var columns = [];
var filterOptionsLoaded = false;
var debtorSearchTimer = null;

function initTable() {
    tblReport = $('#tblReport').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
    });
    columns = [];
    $.each(tblReport.settings()[0].aoColumns, function (key, value) {
        columns.push(value.sWidthOrig);
    });
}

function loadPaidTodayReport() {
    tblPaidToday = $('#tblPaidToday').DataTable({
        destroy: true,
        responsive: true,
        autoWidth: false,
        ajax: {
            url: pathname,
            type: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            data: { action: 'paid_today_report' },
            dataSrc: function (json) {
                if (json && json.error) {
                    message_error(json.error);
                    return [];
                }
                var total = json && json.total ? json.total : '0.00';
                var msg = json && json.message ? json.message : '';
                if (json && json.session) {
                    msg += ' Caja #' + json.session.id + ' abierta: ' + (json.session.opened_at || '');
                }
                $('#paidTodaySummary').html(
                    (msg || 'Pagos del día') + ' · <strong>Total: S/ ' + total + '</strong>'
                );
                return (json && json.rows) ? json.rows : [];
            },
        },
        paging: true,
        pageLength: 10,
        searching: true,
        ordering: true,
        dom: 'Bfrtip',
        buttons: [
            {
                extend: 'excelHtml5',
                text: 'Excel pagos <i class="fas fa-file-excel"></i>',
                className: 'btn btn-success btn-flat btn-xs',
                title: 'Personas que pagaron hoy',
            },
            {
                extend: 'pdfHtml5',
                text: 'Pdf pagos <i class="fas fa-file-pdf"></i>',
                className: 'btn btn-danger btn-flat btn-xs',
                download: 'open',
                orientation: 'landscape',
                pageSize: 'LEGAL',
                title: 'Personas que pagaron hoy',
            },
        ],
        columns: [
            { data: 'date' },
            { data: 'client' },
            { data: 'dni' },
            { data: 'sale_code' },
            { data: 'contract_code' },
            { data: 'concept' },
            { data: 'method' },
            { data: 'amount' },
        ],
        columnDefs: [
            { targets: [0, 2, 3, 4, 6, 7], className: 'text-center' },
            {
                targets: 7,
                render: function (data) {
                    return 'S/ ' + (data || '0.00');
                },
            },
        ],
    });
}

function loadEnrollmentSummaryReport() {
    var parameters = getFilterParams();
    parameters.action = 'enrollment_summary_report';
    tblEnrollmentSummary = $('#tblEnrollmentSummary').DataTable({
        destroy: true,
        responsive: true,
        autoWidth: false,
        ajax: {
            url: pathname,
            type: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            data: parameters,
            dataSrc: function (json) {
                if (json && json.error) {
                    message_error(json.error);
                    return [];
                }
                return Array.isArray(json) ? json : [];
            },
        },
        paging: true,
        pageLength: 10,
        searching: true,
        ordering: true,
        dom: 'Bfrtip',
        buttons: [
            {
                extend: 'excelHtml5',
                text: 'Excel inscritos <i class="fas fa-file-excel"></i>',
                className: 'btn btn-success btn-flat btn-xs',
                title: 'Inscritos por comunidad y centro poblado',
            },
            {
                extend: 'pdfHtml5',
                text: 'Pdf inscritos <i class="fas fa-file-pdf"></i>',
                className: 'btn btn-danger btn-flat btn-xs',
                download: 'open',
                orientation: 'landscape',
                pageSize: 'LEGAL',
                title: 'Inscritos por comunidad y centro poblado',
            },
        ],
        columns: [
            { data: 'community' },
            { data: 'population_center' },
            { data: 'clients_count' },
            { data: 'properties_count' },
        ],
        columnDefs: [
            { targets: [2, 3], className: 'text-center' },
        ],
    });
}

function renderProductEnrollmentSummary(rows) {
    tblProductEnrollmentSummary = $('#tblProductEnrollmentSummary').DataTable({
        destroy: true,
        responsive: true,
        autoWidth: false,
        data: rows || [],
        paging: true,
        pageLength: 10,
        searching: true,
        ordering: true,
        dom: 'Bfrtip',
        buttons: [
            {
                extend: 'excelHtml5',
                text: 'Excel resumen productos <i class="fas fa-file-excel"></i>',
                className: 'btn btn-success btn-flat btn-xs',
                title: 'Inscritos y deudores por producto y comunidad',
            },
            {
                extend: 'pdfHtml5',
                text: 'Pdf resumen productos <i class="fas fa-file-pdf"></i>',
                className: 'btn btn-danger btn-flat btn-xs',
                download: 'open',
                orientation: 'landscape',
                pageSize: 'LEGAL',
                title: 'Inscritos y deudores por producto y comunidad',
            },
        ],
        columns: [
            { data: 'product' },
            { data: 'community' },
            { data: 'population_center' },
            { data: 'clients_count' },
            { data: 'properties_count' },
            { data: 'debtors_count' },
            { data: 'debt_total' },
        ],
        columnDefs: [
            { targets: [3, 4, 5, 6], className: 'text-center' },
            {
                targets: 6,
                render: function (data) {
                    return 'S/ ' + (data || '0.00');
                },
            },
        ],
    });
}

function renderProductDebtorsDetail(rows) {
    tblProductDebtorsDetail = $('#tblProductDebtorsDetail').DataTable({
        destroy: true,
        responsive: true,
        autoWidth: false,
        data: rows || [],
        paging: true,
        pageLength: 10,
        searching: true,
        ordering: true,
        dom: 'Bfrtip',
        buttons: [
            {
                extend: 'excelHtml5',
                text: 'Excel detalle deudores <i class="fas fa-file-excel"></i>',
                className: 'btn btn-success btn-flat btn-xs',
                title: 'Detalle de deudores por producto',
            },
            {
                extend: 'pdfHtml5',
                text: 'Pdf detalle deudores <i class="fas fa-file-pdf"></i>',
                className: 'btn btn-danger btn-flat btn-xs',
                download: 'open',
                orientation: 'landscape',
                pageSize: 'LEGAL',
                title: 'Detalle de deudores por producto',
            },
        ],
        columns: [
            { data: 'product' },
            { data: 'community' },
            { data: 'population_center' },
            { data: 'client' },
            { data: 'dni' },
            { data: 'sale_code' },
            { data: 'contract_code' },
            { data: 'quota' },
            { data: 'paid_quotas' },
            { data: 'paid' },
            { data: 'saldo' },
            { data: 'end_date' },
        ],
        columnDefs: [
            { targets: [4, 5, 6, 7, 8, 9, 10, 11], className: 'text-center' },
            {
                targets: [9, 10],
                render: function (data) {
                    return 'S/ ' + (data || '0.00');
                },
            },
        ],
    });
}

function loadProductEnrollmentDebtReport() {
    var parameters = getFilterParams();
    parameters.action = 'product_enrollment_debt_report';
    $.ajax({
        url: pathname,
        type: 'POST',
        headers: { 'X-CSRFToken': csrftoken },
        data: parameters,
        dataType: 'json',
        success: function (json) {
            if (json && json.error) {
                message_error(json.error);
                return;
            }
            renderProductEnrollmentSummary((json && json.summary) ? json.summary : []);
            renderProductDebtorsDetail((json && json.debtors) ? json.debtors : []);
        },
        error: function () {
            message_error('No se pudo cargar el reporte por producto.');
        },
    });
}

function loadProductQuotaPaymentsReport() {
    var parameters = getFilterParams();
    parameters.action = 'product_quota_payments_report';
    parameters.product = $('#filterProductQuota').val() || '';
    $.ajax({
        url: pathname,
        type: 'POST',
        headers: { 'X-CSRFToken': csrftoken },
        data: parameters,
        dataType: 'json',
        success: function (json) {
            if (json && json.error) {
                message_error(json.error);
                return;
            }
            renderProductQuotaPayments((json && json.columns) ? json.columns : [], (json && json.rows) ? json.rows : []);
        },
        error: function () {
            message_error('No se pudo cargar la matriz de pagos por producto.');
        },
    });
}

function renderProductQuotaPayments(columns, rows) {
    if (tblProductQuotaPayments) {
        tblProductQuotaPayments.destroy();
        $('#tblProductQuotaPayments').empty().append('<thead></thead><tbody></tbody>');
    }
    var dtColumns = (columns || []).map(function (col) {
        return {
            data: col.data,
            title: col.title,
            defaultContent: '',
        };
    });
    tblProductQuotaPayments = $('#tblProductQuotaPayments').DataTable({
        destroy: true,
        responsive: false,
        scrollX: true,
        autoWidth: false,
        data: rows || [],
        paging: true,
        pageLength: 10,
        searching: true,
        ordering: true,
        dom: 'Bfrtip',
        buttons: [
            {
                extend: 'excelHtml5',
                text: 'Excel matriz cuotas <i class="fas fa-file-excel"></i>',
                className: 'btn btn-success btn-flat btn-xs',
                title: 'Matriz de pagos por producto',
            },
            {
                extend: 'pdfHtml5',
                text: 'Pdf matriz cuotas <i class="fas fa-file-pdf"></i>',
                className: 'btn btn-danger btn-flat btn-xs',
                download: 'open',
                orientation: 'landscape',
                pageSize: 'LEGAL',
                title: 'Matriz de pagos por producto',
            },
        ],
        columns: dtColumns,
        columnDefs: [
            {
                targets: '_all',
                className: 'text-center',
            },
            {
                targets: [0, 1, 2, 3],
                className: 'text-left',
            },
        ],
    });
}

function loadDebtorsReport() {
    tblDebtors = $('#tblDebtors').DataTable({
        destroy: true,
        responsive: true,
        autoWidth: false,
        ajax: {
            url: pathname,
            type: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            data: {
                action: 'debtors_report',
                term: $('#debtorSearch').val() || '',
            },
            dataSrc: function (json) {
                if (json && json.error) {
                    message_error(json.error);
                    return [];
                }
                return Array.isArray(json) ? json : [];
            },
        },
        paging: true,
        pageLength: 10,
        searching: false,
        ordering: true,
        dom: 'Bfrtip',
        buttons: [
            {
                extend: 'excelHtml5',
                text: 'Excel deudores <i class="fas fa-file-excel"></i>',
                className: 'btn btn-success btn-flat btn-xs',
                title: 'Clientes que deben',
            },
            {
                extend: 'pdfHtml5',
                text: 'Pdf deudores <i class="fas fa-file-pdf"></i>',
                className: 'btn btn-danger btn-flat btn-xs',
                download: 'open',
                orientation: 'landscape',
                pageSize: 'LEGAL',
                title: 'Clientes que deben',
            },
        ],
        columns: [
            { data: 'client' },
            { data: 'dni' },
            { data: 'sale_code' },
            { data: 'contract_code' },
            { data: 'total' },
            { data: 'paid' },
            { data: 'saldo' },
            { data: 'end_date' },
        ],
        columnDefs: [
            { targets: [1, 2, 3, 7], className: 'text-center' },
            {
                targets: [4, 5, 6],
                className: 'text-center',
                render: function (data) {
                    return 'S/ ' + (data || '0.00');
                },
            },
        ],
    });
}

function todayYmd() {
    var d = new Date();
    var m = String(d.getMonth() + 1).padStart(2, '0');
    var day = String(d.getDate()).padStart(2, '0');
    return d.getFullYear() + '-' + m + '-' + day;
}

function initDateRanges() {
    var today = todayYmd();
    $('#paymentsStartDate, #paymentsEndDate, #cancellationsStartDate, #cancellationsEndDate').val(today);
}

function loadPaymentsByDayReport() {
    tblPaymentsByDay = $('#tblPaymentsByDay').DataTable({
        destroy: true,
        responsive: true,
        autoWidth: false,
        ajax: {
            url: pathname,
            type: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            data: {
                action: 'payments_by_day_report',
                start_date: $('#paymentsStartDate').val() || '',
                end_date: $('#paymentsEndDate').val() || '',
            },
            dataSrc: function (json) {
                if (json && json.error) {
                    message_error(json.error);
                    return [];
                }
                return Array.isArray(json) ? json : [];
            },
        },
        paging: true,
        pageLength: 10,
        searching: true,
        ordering: true,
        dom: 'Bfrtip',
        buttons: [
            {
                extend: 'excelHtml5',
                text: 'Excel pagos por día <i class="fas fa-file-excel"></i>',
                className: 'btn btn-success btn-flat btn-xs',
                title: 'Pagos por días',
            },
            {
                extend: 'pdfHtml5',
                text: 'Pdf pagos por día <i class="fas fa-file-pdf"></i>',
                className: 'btn btn-danger btn-flat btn-xs',
                download: 'open',
                orientation: 'landscape',
                pageSize: 'LEGAL',
                title: 'Pagos por días',
            },
        ],
        columns: [
            { data: 'date' },
            { data: 'count' },
            { data: 'cash' },
            { data: 'yape' },
            { data: 'plin' },
            { data: 'tarjeta' },
            { data: 'total' },
        ],
        columnDefs: [
            { targets: [0, 1], className: 'text-center' },
            {
                targets: [2, 3, 4, 5, 6],
                className: 'text-center',
                render: function (data) {
                    return 'S/ ' + (data || '0.00');
                },
            },
        ],
    });
}

function loadCancellationsReport() {
    tblCancellations = $('#tblCancellations').DataTable({
        destroy: true,
        responsive: true,
        autoWidth: false,
        ajax: {
            url: pathname,
            type: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            data: {
                action: 'cancellations_report',
                start_date: $('#cancellationsStartDate').val() || '',
                end_date: $('#cancellationsEndDate').val() || '',
            },
            dataSrc: function (json) {
                if (json && json.error) {
                    message_error(json.error);
                    return [];
                }
                return Array.isArray(json) ? json : [];
            },
        },
        paging: true,
        pageLength: 10,
        searching: true,
        ordering: true,
        dom: 'Bfrtip',
        buttons: [
            {
                extend: 'excelHtml5',
                text: 'Excel cancelaciones <i class="fas fa-file-excel"></i>',
                className: 'btn btn-success btn-flat btn-xs',
                title: 'Cancelaciones',
            },
            {
                extend: 'pdfHtml5',
                text: 'Pdf cancelaciones <i class="fas fa-file-pdf"></i>',
                className: 'btn btn-danger btn-flat btn-xs',
                download: 'open',
                orientation: 'landscape',
                pageSize: 'LEGAL',
                title: 'Cancelaciones',
            },
        ],
        columns: [
            { data: 'date' },
            { data: 'client' },
            { data: 'dni' },
            { data: 'sale_code' },
            { data: 'contract_code' },
            { data: 'product' },
            { data: 'quantity' },
            { data: 'estimated_amount' },
            { data: 'motive' },
        ],
        columnDefs: [
            { targets: [0, 2, 3, 4, 6, 7], className: 'text-center' },
            {
                targets: 7,
                render: function (data) {
                    return 'S/ ' + (data || '0.00');
                },
            },
        ],
    });
}

function fillSelect($select, items, emptyLabel) {
    var current = $select.val();
    $select.find('option:not(:first)').remove();
    (items || []).forEach(function (item) {
        $select.append($('<option></option>').attr('value', item).text(item));
    });
    if (current && $select.find('option[value="' + current.replace(/"/g, '\\"') + '"]').length) {
        $select.val(current);
    } else {
        $select.val('');
    }
}

function loadFilterOptions(callback) {
    $.ajax({
        url: pathname,
        type: 'POST',
        headers: { 'X-CSRFToken': csrftoken },
        data: { action: 'filter_options' },
        dataType: 'json',
        success: function (data) {
            if (data.error) {
                message_error(data.error);
                return;
            }
            fillSelect($('#filterCommunity'), data.communities || []);
            fillSelect($('#filterPopulationCenter'), data.population_centers || []);
            fillSelect($('#filterProvince'), data.provinces || []);
            fillSelect($('#filterDistrict'), data.districts || []);
            fillProductSelect($('#filterProductQuota'), data.products || []);
            filterOptionsLoaded = true;
            if (typeof callback === 'function') {
                callback();
            }
        },
        error: function () {
            message_error('No se pudieron cargar los filtros.');
        },
    });
}

function fillProductSelect($select, items) {
    var current = $select.val();
    $select.find('option:not(:first)').remove();
    (items || []).forEach(function (item) {
        $select.append($('<option></option>').attr('value', item.id).text(item.name));
    });
    if (current && $select.find('option[value="' + current + '"]').length) {
        $select.val(current);
    } else {
        $select.val('');
    }
}

function getFilterParams() {
    return {
        action: 'search_report',
        location_type: $('#filterLocationType').val() || '',
        community: $('#filterCommunity').val() || '',
        population_center: $('#filterPopulationCenter').val() || '',
        province: $('#filterProvince').val() || '',
        district: $('#filterDistrict').val() || '',
    };
}

function clearFilters() {
    $('#filterLocationType').val('');
    $('#filterCommunity').val('');
    $('#filterPopulationCenter').val('');
    $('#filterProvince').val('');
    $('#filterDistrict').val('');
}

function generateReport(clear) {
    if (clear) {
        clearFilters();
    }
    var parameters = getFilterParams();
    loadEnrollmentSummaryReport();
    loadProductEnrollmentDebtReport();
    loadProductQuotaPaymentsReport();

    tblReport = $('#tblReport').DataTable({
        destroy: true,
        responsive: true,
        autoWidth: false,
        ajax: {
            url: pathname,
            type: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            data: parameters,
            dataSrc: function (json) {
                if (json && json.error) {
                    message_error(json.error);
                    return [];
                }
                return json;
            },
        },
        order: [[1, 'asc'], [0, 'asc']],
        paging: true,
        pageLength: 50,
        ordering: true,
        searching: true,
        dom: 'Bfrtip',
        buttons: [
            {
                extend: 'excelHtml5',
                text: 'Descargar Excel <i class="fas fa-file-excel"></i>',
                titleAttr: 'Excel',
                className: 'btn btn-success btn-flat btn-xs',
                title: 'Reporte de clientes',
            },
            {
                extend: 'pdfHtml5',
                text: 'Descargar Pdf <i class="fas fa-file-pdf"></i>',
                titleAttr: 'PDF',
                className: 'btn btn-danger btn-flat btn-xs',
                download: 'open',
                orientation: 'landscape',
                pageSize: 'LEGAL',
                title: 'Reporte de clientes',
                customize: function (doc) {
                    doc.styles = {
                        header: {
                            fontSize: 18,
                            bold: true,
                            alignment: 'center',
                        },
                        tableHeader: {
                            bold: true,
                            fontSize: 10,
                            color: 'white',
                            fillColor: '#2d4154',
                            alignment: 'center',
                        },
                    };
                    if (doc.content[1] && doc.content[1].table && columns.length) {
                        doc.content[1].table.widths = columns;
                    }
                },
            },
        ],
        columns: [
            { data: 'first_name' },
            { data: 'last_name' },
            { data: 'dni' },
            { data: 'process' },
            { data: 'mobile' },
        ],
        columnDefs: [
            {
                targets: [2, 4],
                className: 'text-center',
            },
            {
                targets: 3,
                className: 'text-left',
                render: function (data) {
                    return data || 'Sin proceso';
                },
            },
        ],
    });
}

$(function () {
    initTable();
    initDateRanges();
    loadFilterOptions(function () {
        loadEnrollmentSummaryReport();
        loadProductEnrollmentDebtReport();
        loadProductQuotaPaymentsReport();
        generateReport(false);
    });
    loadPaidTodayReport();
    loadPaymentsByDayReport();
    loadCancellationsReport();
    loadDebtorsReport();

    $('.btnSearchReport').on('click', function () {
        generateReport(false);
    });

    $('.btnSearchAll').on('click', function () {
        generateReport(true);
    });

    $('#filterLocationType').on('change', function () {
        var v = $(this).val();
        if (v === 'community') {
            $('#filterPopulationCenter').val('');
        } else if (v === 'population_center') {
            $('#filterCommunity').val('');
        }
    });

    $('#debtorSearch').on('keyup change', function () {
        clearTimeout(debtorSearchTimer);
        debtorSearchTimer = setTimeout(function () {
            loadDebtorsReport();
        }, 250);
    });

    $('#btnPaymentsByDay').on('click', function () {
        loadPaymentsByDayReport();
    });

    $('#btnCancellationsReport').on('click', function () {
        loadCancellationsReport();
    });

    $('#filterProductQuota').on('change', function () {
        loadProductQuotaPaymentsReport();
    });
});
