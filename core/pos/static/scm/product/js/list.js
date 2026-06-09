function getData() {
    var parameters = {
        'action': 'search',
    };

    $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
        deferRender: true,
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
            {data: "id", defaultContent: ''},
            {data: "name", defaultContent: ''},
            {data: "category.name", defaultContent: ''},
            {data: "price", defaultContent: '0.00'},
            {data: "id", defaultContent: ''},
        ],
        columnDefs: [
            {
                targets: [3],
                class: 'text-center',
                render: function (data, type, row) {
                    var val = data || row.price || row.pvp || '0.00';
                    return 'S/ ' + parseFloat(val).toFixed(2);
                }
            },
            
            {
                targets: [-1],
                class: 'text-center',
                render: function (data, type, row) {
                    var buttons = '';
                    buttons += '<a href="/pos/scm/product/update/' + row.id + '/" class="btn btn-warning btn-xs btn-flat"><i class="fas fa-edit"></i></a> ';
                    buttons += '<a href="/pos/scm/product/delete/' + row.id + '/" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash"></i></a> ';
                    return buttons;
                }
            },
        ],
        rowCallback: function (row, data, index) {

        },
        initComplete: function (settings, json) {

        }
    });
}

$(function () {
    getData();
})