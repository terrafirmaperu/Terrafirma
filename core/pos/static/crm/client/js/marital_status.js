(function (window, $) {
    'use strict';

    var MODAL_STATUSES = {
        casado: '.marital-modal-casado',
        viudo: '.marital-modal-viudo',
        divorciado: '.marital-modal-divorciado',
        separado: '.marital-modal-separado'
    };

    var EXTRA_STATUSES = ['casado', 'viudo', 'divorciado', 'separado'];

    function getFormRoot(formSelector) {
        var $form = $(formSelector);
        if (!$form.length) {
            return null;
        }
        return {
            $form: $form,
            $select: $form.find('[name="marital_status"]'),
            $extras: $form.find('#maritalStatusExtras').first(),
            $casadoBar: $form.find('#maritalCasadoBar').first(),
            $viudoBar: $form.find('#maritalViudoBar').first(),
            $divorciadoBar: $form.find('#maritalDivorciadoBar').first(),
            $separadoBar: $form.find('#maritalSeparadoBar').first(),
            $casadoSummary: $form.find('#maritalCasadoSummary').first(),
            $viudoSummary: $form.find('#maritalViudoSummary').first(),
            $divorciadoSummary: $form.find('#maritalDivorciadoSummary').first(),
            $separadoSummary: $form.find('#maritalSeparadoSummary').first(),
            $modalCasado: $form.find('.marital-modal-casado').first(),
            $modalViudo: $form.find('.marital-modal-viudo').first(),
            $modalDivorciado: $form.find('.marital-modal-divorciado').first(),
            $modalSeparado: $form.find('.marital-modal-separado').first(),
        };
    }

    function fileSummary(ctx, fieldName, urlKey) {
        var input = ctx.$form.find('[name="' + fieldName + '"]')[0];
        if (input && input.files && input.files.length) {
            return input.files[0].name;
        }
        var url = urlKey || fieldName.replace('_certificate', '');
        if (ctx.$form.find('.existing-marital-file a[href*="' + url + '"]').length) {
            return 'Documento adjunto';
        }
        return '';
    }

    function updateSummary(ctx) {
        if (!ctx) {
            return;
        }
        var spouseFirst = $.trim(ctx.$form.find('[name="spouse_first_name"]').val());
        var spouseLast = $.trim(ctx.$form.find('[name="spouse_last_name"]').val());
        var spouseDni = $.trim(ctx.$form.find('[name="spouse_dni"]').val());
        var spouseParts = [];
        if (spouseFirst || spouseLast) {
            spouseParts.push((spouseFirst + ' ' + spouseLast).trim());
        }
        if (spouseDni) {
            spouseParts.push('DNI ' + spouseDni);
        }
        var marriageSummary = fileSummary(ctx, 'marriage_certificate', 'marriage');
        if (marriageSummary) {
            spouseParts.push(marriageSummary);
        }
        ctx.$casadoSummary.text(spouseParts.length ? spouseParts.join(' · ') : '');

        var deathSummary = fileSummary(ctx, 'death_certificate', 'death');
        ctx.$viudoSummary.text(deathSummary);

        var divorceSummary = fileSummary(ctx, 'divorce_certificate', 'divorce');
        ctx.$divorciadoSummary.text(divorceSummary);

        var separationSummary = fileSummary(ctx, 'separation_certificate', 'separation');
        ctx.$separadoSummary.text(separationSummary);
    }

    function spouseLookupPayload(resp) {
        if (!resp || !resp.success) {
            return null;
        }
        if (resp.data) {
            return resp.data;
        }
        if (resp.existing_client && resp.client && resp.client.user) {
            return {
                first_name: resp.client.user.first_name || '',
                last_name: resp.client.user.last_name || '',
            };
        }
        return null;
    }

    function setupSpouseDniLookup(ctx) {
        var $dni = ctx.$form.find('[name="spouse_dni"]');
        var $first = ctx.$form.find('[name="spouse_first_name"]');
        var $last = ctx.$form.find('[name="spouse_last_name"]');
        if (!$dni.length) {
            return;
        }

        $dni.on('keypress.clientMaritalSpouseDni', function (e) {
            if (typeof validate_form_text === 'function') {
                return validate_form_text('numbers', e, null);
            }
        });

        ctx.$form.on('click.clientMaritalSpouseDni', '.btnLookupSpouseDni', function (e) {
            e.preventDefault();
            var dni = $.trim($dni.val());
            if (dni.length < 7 || dni.length > 12) {
                if (typeof message_error === 'function') {
                    message_error('Ingrese un DNI válido entre 7 y 12 dígitos');
                }
                return false;
            }
            var lookupUrl = (typeof pathname !== 'undefined' && pathname) ? pathname : ctx.$form.attr('action');
            var token = (typeof csrftoken !== 'undefined') ? csrftoken : '';
            var $btn = ctx.$form.find('.btnLookupSpouseDni');
            $.ajax({
                url: lookupUrl,
                type: 'POST',
                headers: {
                    'X-CSRFToken': token
                },
                dataType: 'json',
                data: {
                    action: 'lookup_dni',
                    dni: dni
                },
                beforeSend: function () {
                    $btn.prop('disabled', true);
                },
                success: function (resp) {
                    if (!resp.success) {
                        var msg = resp.error || 'No se pudieron obtener los datos del DNI';
                        if (resp.skipped && typeof alert === 'function') {
                            alert(msg);
                        } else if (typeof message_error === 'function') {
                            message_error(msg);
                        }
                        return;
                    }
                    var data = spouseLookupPayload(resp) || {};
                    $first.val(data.first_name || '');
                    $last.val(data.last_name || '');
                    updateSummary(ctx);
                },
                error: function () {
                    if (typeof message_error === 'function') {
                        message_error('No se pudo consultar el API de DNI');
                    }
                },
                complete: function () {
                    $btn.prop('disabled', false);
                }
            });
            return false;
        });
    }

    function appendExistingFile($group, url, label) {
        $group.find('.existing-marital-file').remove();
        if (!url) {
            return;
        }
        $group.append(
            '<div class="mt-2 existing-marital-file">' +
            '<a href="' + url + '" target="_blank" rel="noopener" class="btn btn-xs btn-outline-info">' +
            '<i class="fas fa-file-alt"></i> ' + label + '</a></div>'
        );
    }

    function applyStatus(ctx, status, options) {
        options = options || {};
        if (!ctx || !ctx.$select.length) {
            return;
        }
        var showExtras = EXTRA_STATUSES.indexOf(status) !== -1;
        ctx.$extras.toggle(showExtras);
        ctx.$casadoBar.toggle(status === 'casado');
        ctx.$viudoBar.toggle(status === 'viudo');
        ctx.$divorciadoBar.toggle(status === 'divorciado');
        ctx.$separadoBar.toggle(status === 'separado');
        updateSummary(ctx);
        if (options.openModal && MODAL_STATUSES[status]) {
            ctx.$form.find(MODAL_STATUSES[status]).first().modal('show');
        }
    }

    window.ClientMaritalStatus = {
        init: function (formSelector) {
            var ctx = getFormRoot(formSelector);
            if (!ctx || !ctx.$select.length) {
                return;
            }
            if (ctx.$form.data('maritalStatusInit')) {
                return;
            }
            ctx.$form.data('maritalStatusInit', true);

            var previous = ctx.$select.val() || '';

            ctx.$select.on('change.clientMarital', function () {
                var status = $(this).val() || '';
                var openModal = status !== previous && EXTRA_STATUSES.indexOf(status) !== -1;
                applyStatus(ctx, status, {openModal: openModal});
                previous = status;
            });

            ctx.$form.on(
                'input change',
                '[name="spouse_first_name"], [name="spouse_last_name"], [name="spouse_dni"], ' +
                '[name="marriage_certificate"], [name="death_certificate"], ' +
                '[name="divorce_certificate"], [name="separation_certificate"]',
                function () {
                    updateSummary(ctx);
                }
            );

            ctx.$form.on('click', '.btn-open-marital-casado', function (e) {
                e.preventDefault();
                ctx.$modalCasado.modal('show');
            });
            ctx.$form.on('click', '.btn-open-marital-viudo', function (e) {
                e.preventDefault();
                ctx.$modalViudo.modal('show');
            });
            ctx.$form.on('click', '.btn-open-marital-divorciado', function (e) {
                e.preventDefault();
                ctx.$modalDivorciado.modal('show');
            });
            ctx.$form.on('click', '.btn-open-marital-separado', function (e) {
                e.preventDefault();
                ctx.$modalSeparado.modal('show');
            });

            ctx.$form.find('.marital-modal-casado, .marital-modal-viudo, .marital-modal-divorciado, .marital-modal-separado')
                .on('hidden.bs.modal', function () {
                    updateSummary(ctx);
                });

            setupSpouseDniLookup(ctx);

            applyStatus(ctx, previous, {openModal: false});
        },

        loadData: function (formSelector, clientData) {
            var ctx = getFormRoot(formSelector);
            if (!ctx || !clientData) {
                return;
            }
            var spouse = clientData.spouse || {};
            ctx.$form.find('[name="spouse_first_name"]').val(spouse.first_name || '');
            ctx.$form.find('[name="spouse_last_name"]').val(spouse.last_name || '');
            ctx.$form.find('[name="spouse_dni"]').val(spouse.dni || '');

            appendExistingFile(
                ctx.$form.find('[name="marriage_certificate"]').closest('.form-group'),
                clientData.marriage_certificate || '',
                'Ver acta actual'
            );
            appendExistingFile(
                ctx.$form.find('[name="death_certificate"]').closest('.form-group'),
                clientData.death_certificate || '',
                'Ver acta actual'
            );
            appendExistingFile(
                ctx.$form.find('[name="divorce_certificate"]').closest('.form-group'),
                clientData.divorce_certificate || '',
                'Ver documento actual'
            );
            appendExistingFile(
                ctx.$form.find('[name="separation_certificate"]').closest('.form-group'),
                clientData.separation_certificate || '',
                'Ver documento actual'
            );

            var status = (clientData.marital_status && clientData.marital_status.id)
                ? clientData.marital_status.id
                : (clientData.marital_status || '');
            if (status) {
                ctx.$select.val(status);
            }
            applyStatus(ctx, status || ctx.$select.val() || '', {openModal: false});
        },

        reset: function (formSelector) {
            var ctx = getFormRoot(formSelector);
            if (!ctx) {
                return;
            }
            ctx.$form.find(
                '[name="spouse_first_name"], [name="spouse_last_name"], [name="spouse_dni"]'
            ).val('');
            ctx.$form.find(
                '[name="marriage_certificate"], [name="death_certificate"], ' +
                '[name="divorce_certificate"], [name="separation_certificate"]'
            ).val('');
            ctx.$form.find('.existing-marital-file').remove();
            ctx.$casadoSummary.text('');
            ctx.$viudoSummary.text('');
            ctx.$divorciadoSummary.text('');
            ctx.$separadoSummary.text('');
            applyStatus(ctx, ctx.$select.val() || '', {openModal: false});
        }
    };
})(window, jQuery);
