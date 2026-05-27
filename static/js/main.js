var pathname = window.location.pathname;

/**
 * Reduce el autocompletado del navegador (p. ej. Chrome) en formularios internos.
 * No aplica al login (#frmLogin) para no interferir con el guardado de contraseñas.
 */
function factoraDisableBrowserAutocomplete() {
    $('form').not('#frmLogin').attr('autocomplete', 'off');
    $('form').not('#frmLogin').find('input, textarea').each(function () {
        var $el = $(this);
        var t = ($el.attr('type') || 'text').toLowerCase();
        if (t === 'hidden' || t === 'submit' || t === 'button' || t === 'reset' || t === 'checkbox' || t === 'radio') {
            return;
        }
        if ($el.attr('autocomplete') === undefined || $el.attr('autocomplete') === 'on') {
            $el.attr('autocomplete', 'off');
        }
    });
}

$(function () {

    factoraDisableBrowserAutocomplete();

    $('[data-toggle="tooltip"]').tooltip();

    $('.table')
        .on('draw.dt', function () {
            $('[data-toggle="tooltip"]').tooltip();
        })
        .on('click', 'img', function () {
            var src = $(this).attr('src');
            load_image(src);
        });
});