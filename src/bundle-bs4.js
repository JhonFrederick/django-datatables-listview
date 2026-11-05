import jQuery from 'jquery';
import JSZip from 'jszip';
import pdfMake from 'pdfmake/build/pdfmake';
import pdfFonts from 'pdfmake/build/vfs_fonts';

// Ensure global variables needed by DataTables Buttons are available
const globalObj = typeof window !== 'undefined' ? window : globalThis;
const $ = globalObj.jQuery || jQuery;
globalObj.jQuery = $;
globalObj.$ = $;
globalObj.JSZip = JSZip;
globalObj.pdfMake = pdfMake;

if (pdfFonts && pdfFonts.pdfMake && pdfFonts.pdfMake.vfs) {
  pdfMake.vfs = pdfFonts.pdfMake.vfs;
} else if (pdfFonts && pdfFonts.vfs) {
  pdfMake.vfs = pdfFonts.vfs;
}

// DataTables Core & Extensions (Bootstrap 4 Styling)
import DataTable from 'datatables.net-bs4';
import 'datatables.net-buttons-bs4';
import 'datatables.net-buttons/js/buttons.colVis.mjs';
import 'datatables.net-buttons/js/buttons.html5.mjs';
import 'datatables.net-buttons/js/buttons.print.mjs';
import 'datatables.net-colreorder-bs4';
import 'datatables.net-responsive-bs4';
import 'datatables.net-rowreorder-bs4';
import 'datatables.net-select-bs4';
import 'datatables.net-columncontrol-bs4';

globalObj.DataTable = DataTable;

export default DataTable;
