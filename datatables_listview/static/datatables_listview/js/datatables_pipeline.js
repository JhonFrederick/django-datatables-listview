//
// Pipelining for DataTables (serverSide)
//
//   ajax: DataTable.pipeline({ url: '/mi/url/', pages: 5, data: function (d) { ... } })
//
// Support to DataTables 2.x y 3.x. Uses fetch() and serializes parameters
//
(function (window) {
    'use strict';

    var DT = window.DataTable;

    if (!DT) {
        throw new Error('datatables_pipeline.js: carga DataTables antes de este archivo.');
    }

    // Parameters that change between pages and that do not invalidate the cache
    var PAGING_KEYS = { draw: true, start: true, length: true };

    function clone(value) {
        return typeof structuredClone === 'function'
            ? structuredClone(value)
            : JSON.parse(JSON.stringify(value));
    }

    /*
    * Serialize an object
    */
    function serialize(obj) {
        var pairs = [];

        function add(key, value) {
            if (typeof value === 'function') {
                value = value();
            }
            pairs.push(encodeURIComponent(key) + '=' + encodeURIComponent(value == null ? '' : value));
        }

        function build(prefix, value) {
            if (Array.isArray(value)) {
                value.forEach(function (v, i) {
                    if (/\[\]$/.test(prefix)) {
                        add(prefix, v);
                    }
                    else {
                        build(prefix + '[' + (typeof v === 'object' && v !== null ? i : '') + ']', v);
                    }
                });
            }
            else if (value !== null && typeof value === 'object') {
                Object.keys(value).forEach(function (k) {
                    build(prefix + '[' + k + ']', value[k]);
                });
            }
            else {
                add(prefix, value);
            }
        }

        Object.keys(obj).forEach(function (k) {
            build(k, obj[k]);
        });

        return pairs.join('&').replace(/%20/g, '+');
    }

    function csrfToken() {
        var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return m ? decodeURIComponent(m[1]) : null;
    }

    /*
    * Returns a signature for the request
    */
    function signature(req, url) {
        var o = {};
        Object.keys(req).sort().forEach(function (k) {
            if (!PAGING_KEYS[k]) {
                o[k] = req[k];
            }
        });
        return JSON.stringify([url, o]);
    }

    function pipeline(opts) {
        var conf = Object.assign({
            pages: 5,      // number of pages to cache
            url: '',       // string or function that returns the url (evaluated on each draw)
            data: null,    // function or object with extra parameters (like `ajax.data`)
            method: 'GET', // HTTP method
            headers: {}    // cabeceras extra
        }, opts);

        var cache = { lower: -1, upper: null, sig: null, json: null };
        var seq = 0;         // identify the last request launched
        var pending = null;  // AbortController of the current request

        return function (request, drawCallback, settings) {
            var requestStart = request.start;
            var requestLength = request.length; // -1 = "All"
            var url = typeof conf.url === 'function' ? conf.url() : conf.url;

            // Copy of the request with extra parameters applied (without mutating `request`)
            var full = clone(request);
            if (typeof conf.data === 'function') {
                var d = conf.data(full);
                if (d) {
                    Object.assign(full, d);
                }
            }
            else if (conf.data && typeof conf.data === 'object') {
                Object.assign(full, conf.data);
            }

            var sig = signature(full, url);
            var cacheValid = cache.json !== null && cache.sig === sig;

            var useCache = !settings.clearCache &&
                requestLength > 0 &&
                cacheValid &&
                requestStart >= cache.lower &&
                requestStart + requestLength <= cache.upper;

            settings.clearCache = false;

            if (useCache) {
                var offset = requestStart - cache.lower;
                var cached = Object.assign({}, cache.json);

                cached.draw = request.draw; // actualizar el eco en cada respuesta
                cached.data = clone(cache.json.data.slice(offset, offset + requestLength));

                drawCallback(cached);
                return;
            }

            // ---- Hace falta pedir datos al servidor ----
            var start = requestStart;
            var fetchLength = requestLength;

            if (requestLength > 0) {
                // Al retroceder, pedir un bloque que termine en la página actual
                if (cacheValid && start < cache.lower) {
                    start = Math.max(0, start - requestLength * (conf.pages - 1));
                }
                fetchLength = requestLength * conf.pages;
            }

            full.start = start;
            full.length = fetchLength;

            var token = ++seq;
            if (pending) {
                pending.abort();
            }
            pending = new AbortController();

            var method = String(conf.method).toUpperCase();
            var headers = Object.assign({
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest'
            }, conf.headers);
            var init = {
                method: method,
                headers: headers,
                signal: pending.signal,
                cache: 'no-store',
                credentials: 'same-origin'
            };

            // empty url = current page (same as $.ajax), preserving its query string
            var target = url || window.location.href.replace(/#.*$/, '');
            var qs = serialize(full);

            if (method === 'GET' || method === 'HEAD') {
                target += (target.indexOf('?') === -1 ? '?' : '&') + qs;
            }
            else {
                init.body = qs;
                headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8';
                if (!headers['X-CSRFToken'] && csrfToken()) {
                    headers['X-CSRFToken'] = csrfToken();
                }
            }

            fetch(target, init)
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error('HTTP ' + response.status);
                    }
                    return response.json();
                })
                .then(
                    function (json) {
                        if (token !== seq) {
                            return; // obsolete response
                        }

                        var rows = json.data || [];

                        if (requestLength > 0) {
                            // The cache is only updated with correct responses
                            cache = {
                                lower: start,
                                upper: start + fetchLength,
                                sig: sig,
                                json: json
                            };

                            var off = requestStart - start;
                            json = Object.assign({}, json);
                            json.data = clone(rows.slice(off, off + requestLength));
                        }
                        else {
                            // "All": no caching
                            cache = { lower: -1, upper: null, sig: null, json: null };
                        }

                        drawCallback(json);
                    },
                    function (err) {
                        if ((err && err.name === 'AbortError') || token !== seq) {
                            return;
                        }
                        // DataTables shows it according to DataTable.ext.errMode
                        drawCallback({
                            draw: request.draw,
                            data: [],
                            recordsTotal: 0,
                            recordsFiltered: 0,
                            error: 'Ajax error (' + (err && err.message ? err.message : err) + ')'
                        });
                    }
                );
        };
    }

    DT.pipeline = pipeline;

    // Compatibility: old code that used $.fn.dataTable.pipeline (if jQuery is present)
    if (window.jQuery && window.jQuery.fn && window.jQuery.fn.dataTable) {
        window.jQuery.fn.dataTable.pipeline = pipeline;
    }

    // table.clearPipeline().draw() -> forces a request to the server in the next draw
    DT.Api.register('clearPipeline()', function () {
        return this.iterator('table', function (settings) {
            settings.clearCache = true;
        });
    });
})(window);