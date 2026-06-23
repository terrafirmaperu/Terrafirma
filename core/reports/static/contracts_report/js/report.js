var tblContractsReport;
var columns = [];

function isLocationFiltersEnabled() {
    return $('#toggleContractsLocationFilters').is(':checked');
}

function clearLocationFilters() {
    $('#filterDepartment, #filterProvince, #filterDistrict, #filterCommunity, #filterPopulationCenter').val('');
}

function setLocationFiltersEnabled(enabled) {
    $('#contractsLocationFiltersPanel, #contractsLocationFiltersPanelRow2').toggleClass('d-none', !enabled);
    $('.contracts-location-filter').prop('disabled', !enabled);
    if (!enabled) {
        clearLocationFilters();
    }
}

function fillSelect($select, items, emptyLabel) {
    var current = $select.val();
    $select.find('option:not(:first)').remove();
    (items || []).forEach(function (item) {
        if (typeof item === 'object' && item !== null) {
            $select.append(
                $('<option></option>').attr('value', item.id).text(item.name)
            );
        } else {
            $select.append($('<option></option>').attr('value', item).text(item));
        }
    });
    if (current && $select.find('option[value="' + String(current).replace(/"/g, '\\"') + '"]').length) {
        $select.val(current);
    } else {
        $select.val('');
    }
}

function getFilterParams() {
    var params = {
        action: 'search_report',
        product: $('#filterProduct').val() || '',
        predio_type: $('#filterPredioType').val() || '',
        location_type: $('#filterLocationType').val() || '',
        location_filters_enabled: isLocationFiltersEnabled() ? '1' : '0',
    };
    if (isLocationFiltersEnabled()) {
        params.department = $('#filterDepartment').val() || '';
        params.province = $('#filterProvince').val() || '';
        params.district = $('#filterDistrict').val() || '';
        params.community = $('#filterCommunity').val() || '';
        params.population_center = $('#filterPopulationCenter').val() || '';
    }
    return params;
}

function clearFilters() {
    $('#filterProduct, #filterPredioType, #filterLocationType').val('');
    $('#toggleContractsLocationFilters').prop('checked', false);
    setLocationFiltersEnabled(false);
}

function updateFilterSummary(text, total) {
    $('#contractsFilterSummaryText').text(text || 'Sin filtro');
    if (typeof total === 'number') {
        $('#contractsResultCount').text('Registros encontrados: ' + total);
    } else {
        $('#contractsResultCount').text('');
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
            if (data && data.error) {
                message_error(data.error);
                return;
            }
            fillSelect($('#filterProduct'), data.products || []);
            fillSelect($('#filterDepartment'), data.departments || []);
            fillSelect($('#filterProvince'), data.provinces || []);
            fillSelect($('#filterDistrict'), data.districts || []);
            fillSelect($('#filterCommunity'), data.communities || []);
            fillSelect($('#filterPopulationCenter'), data.population_centers || []);
            fillSelect($('#filterPredioType'), data.predio_types || []);
            if (typeof callback === 'function') {
                callback();
            }
        },
        error: function () {
            message_error('No se pudieron cargar los filtros.');
        },
    });
}

function generateContractsReport(clearFiltersFirst) {
    if (clearFiltersFirst) {
        clearFilters();
    }
    var parameters = getFilterParams();

    tblContractsReport = $('#tblContractsReport').DataTable({
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
                    updateFilterSummary('Error al aplicar filtro', 0);
                    return [];
                }
                updateFilterSummary(json.filter_summary || '', json.total || 0);
                return (json && json.rows) ? json.rows : [];
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
                text: 'Excel <i class="fas fa-file-excel"></i>',
                className: 'btn btn-success btn-flat btn-xs',
                title: function () {
                    return 'Contratos — ' + ($('#contractsFilterSummaryText').text() || '');
                },
            },
            {
                extend: 'pdfHtml5',
                text: 'Pdf <i class="fas fa-file-pdf"></i>',
                className: 'btn btn-danger btn-flat btn-xs',
                download: 'open',
                orientation: 'landscape',
                pageSize: 'LEGAL',
                title: function () {
                    return 'Contratos — ' + ($('#contractsFilterSummaryText').text() || '');
                },
                customize: function (doc) {
                    if (doc.content[1] && doc.content[1].table && columns.length) {
                        doc.content[1].table.widths = columns;
                    }
                },
            },
        ],
        columns: [
            { data: 'first_name' },
            { data: 'last_name' },
            { data: 'marital_status' },
            { data: 'mobile' },
            { data: 'dni' },
        ],
        columnDefs: [
            { targets: [2, 3, 4], className: 'text-center' },
        ],
    });

    columns = [];
    $.each(tblContractsReport.settings()[0].aoColumns, function (key, value) {
        columns.push(value.sWidthOrig);
    });
}

$(function () {
    setLocationFiltersEnabled(false);

    loadFilterOptions(function () {
        generateContractsReport(false);
    });

    $('#toggleContractsLocationFilters').on('change', function () {
        setLocationFiltersEnabled($(this).is(':checked'));
    });

    $('#btnContractsSearch').on('click', function () {
        generateContractsReport(false);
    });

    $('#btnContractsClear').on('click', function () {
        generateContractsReport(true);
    });

    $('#filterLocationType').on('change', function () {
        if (!isLocationFiltersEnabled()) {
            return;
        }
        var value = $(this).val();
        if (value === 'community') {
            $('#filterPopulationCenter').val('');
        } else if (value === 'population_center') {
            $('#filterCommunity').val('');
        }
    });
});
