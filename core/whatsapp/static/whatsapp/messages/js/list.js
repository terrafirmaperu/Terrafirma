function getData() {
    $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
        deferRender: true,
        ajax: {
            url: pathname,
            type: 'POST',
            headers: {'X-CSRFToken': csrftoken},
            data: {action: 'search'},
            dataSrc: ''
        },
        columns: [
            {data: 'id'},
            {data: 'name'},
            {data: 'message_preview'},
            {
                data: null,
                render: function (data, type, row) {
                    if (row.recipient_source === 'filter' && row.filter_summary) {
                        return row.filter_summary;
                    }
                    return row.recipient_source_label || '';
                },
            },
            {data: 'status_label'},
            {data: 'sent_count'},
            {data: 'date_joined'},
            {data: 'id'},
        ],
        columnDefs: [
            {
                targets: [-3, -2],
                className: 'text-center',
            },
            {
                targets: [-1],
                className: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    var buttons = '';
                    if (row.status === 'draft' || row.status === 'failed' || row.status === 'partial') {
                        buttons += '<button type="button" class="btn btn-success btn-xs btn-flat btnResend" data-id="' + row.id + '"><i class="fas fa-paper-plane"></i></button> ';
                    }
                    buttons += '<a href="/whatsapp/messages/delete/' + row.id + '/" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash"></i></a> ';
                    return buttons;
                }
            },
        ],
    });
}

$(function () {
    getData();

    $('#data').on('click', '.btnResend', function () {
        var id = $(this).data('id');
        var $btn = $(this);
        $btn.prop('disabled', true);
        $.ajax({
            url: '/whatsapp/messages/add/',
            type: 'POST',
            headers: {'X-CSRFToken': csrftoken},
            dataType: 'json',
            data: {action: 'send_existing', id: id},
            success: function (resp) {
                if (resp.error) {
                    message_error(typeof resp.error === 'string' ? resp.error : 'Error al enviar');
                    return;
                }
                message_success('Envío procesado.');
                getData();
            },
            error: function () {
                message_error('No se pudo enviar el mensaje.');
            },
            complete: function () {
                $btn.prop('disabled', false);
            }
        });
    });
});
