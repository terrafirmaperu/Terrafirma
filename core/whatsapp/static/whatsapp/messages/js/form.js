var fv;

function recipientSourceValue() {
    return $('#id_recipient_source').val();
}

function locationBaseValue() {
    return $('#filter_location_base').val() || 'predio';
}

function toggleRecipientBlocks() {
    var source = recipientSourceValue();
    $('#manualRecipientsBlock').toggle(source === 'manual');
    $('#filterRecipientsBlock').toggle(source === 'filter');
}

function toggleLocationBaseFields() {
    var isClient = locationBaseValue() === 'client';
    $('#predioLocationFields').toggle(!isClient);
    $('#clientLocationFields').toggle(isClient);
}

function previewPayload() {
    var base = locationBaseValue();
    var data = {
        action: 'preview_count',
        recipient_source: recipientSourceValue(),
        recipients_text: $('#id_recipients_text').val(),
        filter_audience: $('#filter_audience').val(),
        filter_location_base: base,
        filter_product: $('#filter_product').val(),
        filter_department: '',
        filter_community: '',
        filter_population_center: '',
        filter_province: '',
        filter_district: '',
        filter_predio_department: '',
        filter_predio_address: '',
        filter_client_province: '',
        filter_client_district: '',
        filter_client_address: '',
    };
    if (base === 'client') {
        data.filter_department = $('#filter_department').val();
        data.filter_client_province = $('#filter_client_province').val();
        data.filter_client_district = $('#filter_client_district').val();
        data.filter_client_address = $('#filter_client_address').val();
    } else {
        data.filter_predio_department = $('#filter_predio_department').val();
        data.filter_predio_address = $('#filter_predio_address').val();
        data.filter_community = $('#filter_community').val();
        data.filter_population_center = $('#filter_population_center').val();
        data.filter_province = $('#filter_province').val();
        data.filter_district = $('#filter_district').val();
    }
    return data;
}

document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('frmForm');
    fv = FormValidation.formValidation(form, {
            locale: 'es_ES',
            localization: FormValidation.locales.es_ES,
            plugins: {
                trigger: new FormValidation.plugins.Trigger(),
                submitButton: new FormValidation.plugins.SubmitButton(),
                bootstrap: new FormValidation.plugins.Bootstrap(),
                icon: new FormValidation.plugins.Icon({
                    valid: 'fa fa-check',
                    invalid: 'fa fa-times',
                    validating: 'fa fa-refresh',
                }),
            },
            fields: {
                name: {
                    validators: {notEmpty: {message: 'Indique un nombre'}},
                },
                message_body: {
                    validators: {notEmpty: {message: 'Escriba el mensaje'}},
                },
            },
        }
    ).on('core.form.valid', function () {
        submit_formdata_with_ajax_form(fv);
    });
});

$(function () {
    toggleRecipientBlocks();
    toggleLocationBaseFields();

    $('#id_recipient_source').on('change', function () {
        toggleRecipientBlocks();
        $('#recipientCount').val('—');
    });

    $('#filter_location_base').on('change', function () {
        toggleLocationBaseFields();
        $('#recipientCount').val('—');
    });

    $('#btnPreviewCount').on('click', function () {
        $.ajax({
            url: pathname,
            type: 'POST',
            headers: {'X-CSRFToken': csrftoken},
            dataType: 'json',
            data: previewPayload(),
            success: function (resp) {
                $('#recipientCount').val(resp.count != null ? resp.count : '0');
            },
        });
    });

    $('#filterRecipientsBlock select, #filterRecipientsBlock input[type="text"]').on('change input', function () {
        $('#recipientCount').val('—');
    });

    $('#btnSaveDraft').on('click', function () {
        $('#send_now').val('0');
    });

    $('#btnSendNow').on('click', function (e) {
        e.preventDefault();
        $('#send_now').val('1');
        fv.validate().then(function (status) {
            if (status === 'Valid') {
                submit_formdata_with_ajax_form(fv);
            }
        });
    });
});
