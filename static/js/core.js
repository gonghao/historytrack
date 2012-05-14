(function() {
    var doc = document;

    var fakeLink = doc.createElement('a'),
        hostName = location.host;

    function adjustUrl(url) {
        var pathname;

        fakeLink.href = url;

        if (fakeLink.protocol !== 'http:') {
            return url;
        }

        if (hostName === fakeLink.host) {
            if ((pathname = fakeLink.pathname) && pathname.indexOf('/link/') !== 0) {
                fakeLink.href = decodeURIComponent(location.pathname).replace('/link/', '');
                url = location.origin + '/link/' + encodeURIComponent(fakeLink.origin + pathname);
            }
        } else {
            url = location.origin + '/link/' + encodeURIComponent(url);
        }

        return encodeURI(url);
    }

    function init() {
        var i, len;

        var as = doc.getElementsByTagName('a'), a;

        for (i = 0, len = as.length; i < len; i++) {
            a = as[i];

            a.href = adjustUrl(a.href);
        }

        var forms = doc.getElementsByTagName('form'), f;

        for (i = 0, len = forms.length; i < len; i++) {
            f = forms[i];

            f.action = adjustUrl(f.action);
        }
    }

    doc.addEventListener('DOMContentLoaded', function(evt) {
        init();
    }, false);
})();
