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

function getData() {
    const csrftoken = getCookie('csrftoken');
    $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
        deferRender: false,
        ajax: {
            url: pathname,
            type: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            },
            data: {
                'action': 'search'
            },
            dataSrc: "",
            error: function(xhr, status, error) {
                console.log('Error en Ajax:', error);
                console.log('Status:', status);
                console.log('Response:', xhr.responseText);
            }
        },
        columns: [
            {data: "id"},
            {
                data: "client_code",
                render: function (data, type, row) {
                    return row.client_code || '—';
                }
            },
            {
                data: null,
                render: function(data, type, row) {
                    return row.user.full_name;
                }
            },
            {
                data: null,
                render: function(data, type, row) {
                    return row.user.dni;
                }
            },
            {data: "mobile"},
            {
                data: null,
                render: function(data, type, row) {
                    var parts = [];
                    if (row.department) parts.push(row.department);
                    if (row.province) parts.push(row.province);
                    if (row.district) parts.push(row.district);
                    var ubigeo = parts.length ? parts.join(' / ') : '';
                    var dir = row.address || '';
                    if (ubigeo && dir) {
                        return ubigeo + '<br><small class="text-muted">' + dir + '</small>';
                    }
                    return ubigeo || dir || '—';
                }
            },
            {data: "id"},
        ],
        columnDefs: [
            {
                targets: [-1],
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    var buttons = '<a href="/pos/crm/client/update/' + row.id + '/" class="btn btn-warning btn-xs btn-flat"><i class="fas fa-edit"></i></a> ';
                    buttons += '<a href="/pos/crm/client/delete/' + row.id + '/" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash-alt"></i></a>';
                    return buttons;
                }
            },
        ],
        initComplete: function (settings, json) {

        }
    });
}

$(function () {
    getData();
});