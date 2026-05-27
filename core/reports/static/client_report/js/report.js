var tblReport;
var columns = [];
var filterOptionsLoaded = false;

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
    loadFilterOptions(function () {
        generateReport(false);
    });

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
});
