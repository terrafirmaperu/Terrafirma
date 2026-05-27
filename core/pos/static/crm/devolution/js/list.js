var tblDevolution;
var input_daterange;
var select_sale;

function getData(all) {
    var parameters = {
        'action': 'search',
        'sale': select_sale.val(),
        'start_date': input_daterange.data('daterangepicker').startDate.format('YYYY-MM-DD'),
        'end_date': input_daterange.data('daterangepicker').endDate.format('YYYY-MM-DD'),
    };

    if (all) {
        parameters['start_date'] = '';
        parameters['end_date'] = '';
    }

    tblDevolution = $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
        ajax: {
            url: pathname,
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: parameters,
            dataSrc: ""
        },
        columns: [
            {data: "id"},
            {data: "saledetail.sale.nro"},
            {data: "saledetail.product.name"},
            {data: "date_joined"},
            {data: "cant"},
            {data: "motive"},
            {data: "id"},
        ],
        columnDefs: [
            {
                targets: [-1],
                orderable: false,
                class: 'text-center',
                render: function (data, type, row) {
                    return '<a href="/pos/crm/devolution/delete/' + row.id + '/" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash"></i></a>';
                }
            },
        ],
        initComplete: function (settings, json) {

        }
    });
}

$(function () {

    input_daterange = $('input[name="date_range"]');
    select_sale = $('select[name="sale"]');

    input_daterange
        .daterangepicker({
            language: 'auto',
            startDate: new Date(),
            locale: {
                format: 'YYYY-MM-DD',
            }
        })
        .on('apply.daterangepicker', function (ev, picker) {
            getData(false);
        });

    $('.select2').select2({
        theme: 'bootstrap4',
        language: "es"
    });

    select_sale.on('change', function () {
        getData(false);
    });

    $('.drp-buttons').hide();

    getData(false);

    $('.btnSearch').on('click', function () {
        getData(false);
    });

    $('.btnSearchAll').on('click', function () {
        getData(true);
    });
});
