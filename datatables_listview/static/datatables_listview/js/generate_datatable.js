(function () {
    'use strict';

    function ready(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    // Read an optional global variable (declared with var, let or const) without throwing an error
    function optionalGlobal(read) {
        try {
            var value = read();
            return typeof value === 'undefined' ? null : value;
        } catch (err) {
            return null;
        }
    }

    ready(function () {

        // ---- Optional configuration defined from the template -------------------------------
        var userButtons = optionalGlobal(function () { return custom_buttons; });
        var finalPageLength = optionalGlobal(function () { return custom_page_length; }) || 10;
        var finalCachePages = optionalGlobal(function () { return custom_cache_pages; }) || 5;
        // Todo: Add the possibility to define this buttons from the view
        var finalButtons = userButtons || [
            { extend: 'copy', exportOptions: { columns: ':not(:last)' }, text: 'Copy' },
            { extend: 'csv', exportOptions: { columns: ':not(:last)' }, text: 'CSV' },
            { extend: 'excel', exportOptions: { columns: ':not(:last)' }, text: 'Excel' },
            { extend: 'pdf', exportOptions: { columns: ':not(:last)' }, text: 'PDF' },
            {
                extend: 'print',
                customize: function (win) {
                    var body = win.document.body;
                    body.classList.add('white-bg');
                    body.style.fontSize = '10px';

                    body.querySelectorAll('table').forEach(function (table) {
                        table.classList.add('compact');
                        table.style.fontSize = 'inherit';
                    });
                },
                exportOptions: { columns: ':not(:last)' },
                text: 'Imprimir'
            },
            {
                extend: 'colvis',
                exportOptions: { columns: ':not(:last)' },
                text: 'Mostrar/Ocultar columnas'
            }
        ];

        // ---- Column definition -------------
        var columns = column_defs.slice();
        if (options) {
            columns.push({
                title: title_column_options,
                targets: columns.length,
                orderable: false,
                searchable: false,
                responsivePriority: 0
            });
        }

        // ---- Table ----------------------------------------------------------------------------
        // Current URL of the table; the pipeline reads it in each draw. Change it (filters)
        // invalidates the cache automatically. '' = current page.
        var tableUrl = '';

        var table = new DataTable('#datatable-view', {
            dom: 'Br<"d-flex justify-content-between flex-wrap"lf>t<"d-flex justify-content-between flex-wrap"ip>',
            responsive: true,
            autoWidth: false,
            pageLength: finalPageLength,
            columnDefs: columns,
            serverSide: true,
            processing: true,
            ajax: DataTable.pipeline({
                url: function () { return tableUrl; },
                pages: finalCachePages // Number of pages to cache
            }),
            buttons: finalButtons,
            language: {
                url: cdn_language
            },
            order: [default_column_order]
        });

        window.customDatatable = table;
        table.table().header().classList.add('text-muted');

        // ---- External filters -----------------------------------------------------------------
        var filters = document.querySelectorAll('[data-table-filter]');

        function filterValue(el) {
            if (el.type === 'checkbox') {
                return el.checked ? 'True' : '';
            }
            if (el.multiple) {
                return Array.from(el.selectedOptions).map(function (o) { return o.value; }).join(',');
            }
            return el.value;
        }

        function applyFilters() {
            var url = new URL(window.location.href);
            url.hash = '';

            filters.forEach(function (el) {
                url.searchParams.append('column_only', el.getAttribute('name'));
                url.searchParams.append('value_only', filterValue(el));
            });

            var newUrl = url.toString();
            if (newUrl === tableUrl) {
                return; // nothing changed: avoid repeated requests by "click"
            }

            tableUrl = newUrl;
            table.clearPipeline().draw(); // Return to first page
        }

        filters.forEach(function (el) {
            el.addEventListener('change', applyFilters);
            el.addEventListener('click', applyFilters);
        });
    });
})();
