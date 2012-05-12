(function() {
    var doc = document;

    function init() {
        var as = doc.getElementsByTagName('a'),
            a,
            i = 0, len = as.length,
            hostName = location.host;

        for (; i < len; i++) {
            a = as[i];

            if (hostName !== a.host && a.protocol === 'http:') {
                a.href = '/link/' + a.href;
            }
        }
    }

    doc.addEventListener('DOMContentLoaded', function(evt) {
        init();
    }, false);
})();
