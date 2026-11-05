(function (global) {
    'use strict';

    /**
     * Server-side DataTable wired to a DatatablesListView.
     *
     * Every aspect of the configuration is a method, so behaviour can be changed by
     * subclassing and overriding only what is needed. Initialization is up to the caller:
     *
     *   class MyTable extends DatatableListView {
     *       getButtons() {
     *           return super.getButtons().filter(function (b) { return b.extend !== 'pdf'; });
     *       }
     *   }
     *   new MyTable(window.datatableListViewConfig).init();
     */
    class DatatableListView {
        /**
         * @param {Object} config
         * @param {string} [config.selector='#datatable-view']
         * @param {Array}  [config.columnDefs=[]]      Column definitions from the view
         * @param {boolean} [config.showOptions=false] Adds the options column at the end
         * @param {string} [config.optionsTitle='']    Title of the options column
         * @param {Array}  [config.defaultOrder=[0, 'asc']]
         * @param {string} [config.languageUrl]        DataTables language file URL
         * @param {Array}  [config.buttons]            Replaces the default buttons
         * @param {number} [config.pageLength=10]
         * @param {number} [config.cachePages=5]       Pages cached by the pipeline
         */
        constructor(config) {
            config = config || {};
            this.selector = config.selector || '#datatable-view';
            this.columnDefs = config.columnDefs || [];
            this.showOptions = !!config.showOptions;
            this.optionsTitle = config.optionsTitle || '';
            this.defaultOrder = config.defaultOrder || [0, 'asc'];
            this.languageUrl = config.languageUrl || null;
            this.buttons = config.buttons || null;
            this.pageLength = config.pageLength || 10;
            this.cachePages = config.cachePages || 5;

            this.table = null;     // DataTables API instance
            this.filters = [];     // External filter elements ([data-table-filter])
            this.tableUrl = '';    // Current URL; '' = current page. Changing it invalidates the cache
        }

        // ---- Configuration (override these to customize) -----------------------------------

        getColumns() {
            var columns = this.columnDefs.slice();
            if (this.showOptions) {
                columns.push({
                    title: this.optionsTitle,
                    targets: columns.length,
                    orderable: false,
                    searchable: false,
                    responsivePriority: 0
                });
            }
            return columns;
        }

        getDefaultButtons() {
            return [
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
                    text: 'Print'
                },
                {
                    extend: 'colvis',
                    exportOptions: { columns: ':not(:last)' },
                    text: 'Show/Hide columns'
                }
            ];
        }

        getButtons() {
            return this.buttons || this.getDefaultButtons();
        }

        getDom() {
            return 'Br<"d-flex justify-content-between flex-wrap"lf>t<"d-flex justify-content-between flex-wrap"ip>';
        }

        getPipelineUrl() {
            var self = this;
            return function () { return self.tableUrl; };
        }

        getOptions() {
            return {
                dom: this.getDom(),
                responsive: true,
                autoWidth: false,
                pageLength: this.pageLength,
                columnDefs: this.getColumns(),
                serverSide: true,
                processing: true,
                ajax: DataTable.pipeline({
                    url: this.getPipelineUrl(),
                    pages: this.cachePages
                }),
                buttons: this.getButtons(),
                language: { url: this.languageUrl },
                order: [this.defaultOrder]
            };
        }

        // ---- Lifecycle ----------------------------------------------------------------------

        init() {
            this.table = new DataTable(this.selector, this.getOptions());
            global.customDatatable = this.table; // Backward compatibility
            this.table.table().header().classList.add('text-muted');
            this.bindFilters();
            return this;
        }

        // ---- External filters ---------------------------------------------------------------

        getFilterValue(el) {
            if (el.type === 'checkbox') {
                return el.checked ? 'True' : '';
            }
            if (el.multiple) {
                return Array.from(el.selectedOptions).map(function (o) { return o.value; }).join(',');
            }
            return el.value;
        }

        bindFilters() {
            var self = this;
            this.filters = Array.from(document.querySelectorAll('[data-table-filter]'));
            this.filters.forEach(function (el) {
                el.addEventListener('change', function () { self.applyFilters(); });
                el.addEventListener('click', function () { self.applyFilters(); });
            });
        }

        applyFilters() {
            var self = this;
            var url = new URL(window.location.href);
            url.hash = '';

            this.filters.forEach(function (el) {
                url.searchParams.append('column_only', el.getAttribute('name'));
                url.searchParams.append('value_only', self.getFilterValue(el));
            });

            var newUrl = url.toString();
            if (newUrl === this.tableUrl) {
                return; // nothing changed: avoid repeated requests by "click"
            }

            this.tableUrl = newUrl;
            this.table.clearPipeline().draw(); // Return to first page
        }
    }

    global.DatatableListView = DatatableListView;
})(window);
