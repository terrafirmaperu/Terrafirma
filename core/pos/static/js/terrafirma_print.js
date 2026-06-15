(function (global) {
    'use strict';

    var POPUP_FEATURES = 'width=1,height=1,left=0,top=0,toolbar=0,menubar=0,location=0,status=0';

    function buildPrintUrl(baseUrl, voucher) {
        var sep = baseUrl.indexOf('?') >= 0 ? '&' : '?';
        return baseUrl + sep + 'format=html&auto=popup&t=' + Date.now();
    }

    function printViaIframe(url) {
        var iframeUrl = url.replace('auto=popup', 'auto=iframe');
        var iframe = document.createElement('iframe');
        iframe.setAttribute('aria-hidden', 'true');
        iframe.style.cssText = 'position:fixed;width:1px;height:1px;left:0;top:0;border:0;opacity:0;pointer-events:none';
        var cleaned = false;

        function cleanup() {
            if (cleaned) {
                return;
            }
            cleaned = true;
            global.removeEventListener('message', onMessage);
            if (iframe.parentNode) {
                iframe.parentNode.removeChild(iframe);
            }
        }

        function onMessage(event) {
            if (event && event.data === 'terrafirma-print-done') {
                cleanup();
            }
        }

        global.addEventListener('message', onMessage);
        setTimeout(cleanup, 20000);
        document.body.appendChild(iframe);
        iframe.src = iframeUrl;
    }

    function printViaNavigate(url) {
        try {
            sessionStorage.setItem('terrafirma_print_return', global.location.pathname + global.location.search);
        } catch (e) {
            /* ignore */
        }
        global.location.href = url.replace('auto=popup', 'auto=1');
    }

    function openTerrafirmaPrint(baseUrl) {
        if (!baseUrl) {
            return;
        }
        var url = buildPrintUrl(baseUrl);
        var winName = 'terrafirma_print_' + String(Date.now());
        var printWin;

        try {
            printWin = global.open(url, winName, POPUP_FEATURES);
        } catch (e) {
            printWin = null;
        }

        if (printWin) {
            return;
        }

        printViaIframe(url);
    }

    global.TerrafirmaPrint = {
        open: openTerrafirmaPrint,
        popupFeatures: POPUP_FEATURES,
        printViaNavigate: printViaNavigate
    };
}(window));
