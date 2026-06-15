(function (global) {
    'use strict';

    function mmFromPx(px) {
        return Math.ceil(px * 0.264583);
    }

    function setPageSize80() {
        var root = document.querySelector('.thermal-80') || document.body;
        var px = Math.max(
            root.scrollHeight || 0,
            root.offsetHeight || 0,
            document.body.scrollHeight || 0,
            280
        );
        var mmH = Math.max(110, mmFromPx(px) + 12);
        var el = document.getElementById('thermal-80-page-style');
        if (!el) {
            el = document.createElement('style');
            el.id = 'thermal-80-page-style';
            document.head.appendChild(el);
        }
        el.textContent =
            '@page { size: 80mm ' + mmH + 'mm; margin: 0; }' +
            'html, body { width: 80mm !important; min-height: ' + mmH + 'mm !important; margin: 0; padding: 0; }';
    }

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

    function runPrint(afterPrint) {
        setPageSize80();
        window.focus();
        window.print();
        if (typeof afterPrint === 'function') {
            setTimeout(afterPrint, 200);
        }
    }

    function waitThenPrint(afterPrint, maxWaitMs) {
        maxWaitMs = maxWaitMs || 2500;
        var finished = false;

        function trigger() {
            if (finished) {
                return;
            }
            finished = true;
            setTimeout(function () {
                runPrint(afterPrint);
            }, 120);
        }

        setTimeout(trigger, maxWaitMs);

        whenReady(function () {
            var imgs = document.images;
            if (!imgs.length) {
                trigger();
                return;
            }
            var pending = 0;
            var i;
            for (i = 0; i < imgs.length; i++) {
                if (!imgs[i].complete) {
                    pending++;
                }
            }
            if (!pending) {
                trigger();
                return;
            }
            var done = 0;
            function imageDone() {
                done++;
                if (done >= pending) {
                    trigger();
                }
            }
            for (i = 0; i < imgs.length; i++) {
                if (!imgs[i].complete) {
                    imgs[i].onload = imageDone;
                    imgs[i].onerror = imageDone;
                }
            }
        });
    }

    function runAutoPrint(mode) {
        if (!mode) {
            return;
        }
        if (mode === 'popup') {
            waitThenPrint(function () {
                window.close();
            });
            return;
        }
        if (mode === '1') {
            waitThenPrint(goBack);
        }
    }

    global.ThermalPrint80 = {
        runAutoPrint: runAutoPrint,
        setPageSize80: setPageSize80,
        popupFeatures: 'width=420,height=720,left=-2400,top=0,toolbar=0,menubar=0,location=0,status=0,resizable=0,scrollbars=0'
    };
}(window));
