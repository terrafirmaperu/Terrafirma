(function (global) {
    'use strict';

    function whenReady(fn) {
        if (document.readyState === 'complete') {
            fn();
        } else {
            window.addEventListener('load', fn, { once: true });
        }
    }

    function goBack() {
        var ret = null;
        try {
            ret = sessionStorage.getItem('terrafirma_print_return');
            sessionStorage.removeItem('terrafirma_print_return');
        } catch (e) {
            /* ignore */
        }
        if (ret) {
            window.location.replace(ret);
        } else {
            window.history.back();
        }
    }

    function notifyParentDone() {
        try {
            if (window.parent && window.parent !== window) {
                window.parent.postMessage('terrafirma-print-done', '*');
            }
        } catch (e) {
            /* ignore */
        }
    }

    function runPrint(afterPrint) {
        var finished = false;

        function finish() {
            if (finished) {
                return;
            }
            finished = true;
            notifyParentDone();
            if (typeof afterPrint === 'function') {
                setTimeout(afterPrint, 150);
            }
        }

        window.onafterprint = finish;
        setTimeout(finish, 8000);
        window.focus();
        window.print();
    }

    function runAutoPrint(mode) {
        if (!mode) {
            return;
        }

        if (mode === 'popup') {
            whenReady(function () {
                setTimeout(function () {
                    runPrint(function () {
                        window.close();
                    });
                }, 120);
            });
            return;
        }

        if (mode === 'iframe') {
            whenReady(function () {
                setTimeout(function () {
                    runPrint(null);
                }, 120);
            });
            return;
        }

        if (mode === '1') {
            whenReady(function () {
                setTimeout(function () {
                    runPrint(goBack);
                }, 120);
            });
        }
    }

    global.TerrafirmaTicketAutoPrint = {
        run: runAutoPrint
    };
}(window));
