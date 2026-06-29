$(function () {
    if ($('#data tbody tr td[colspan]').length) {
        return;
    }
    $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        order: [[0, 'desc']],
        pageLength: 50,
        dom: 'frtip',
        language: {
            url: '//cdn.datatables.net/plug-ins/1.10.25/i18n/Spanish.json',
        },
    });
});
