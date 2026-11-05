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

// DataTables Core & Extensions (Default Styling)
import DataTable from 'datatables.net-dt';
import 'datatables.net-buttons-dt';
import 'datatables.net-buttons/js/buttons.colVis.mjs';
import 'datatables.net-buttons/js/buttons.html5.mjs';
import 'datatables.net-buttons/js/buttons.print.mjs';
import 'datatables.net-colreorder-dt';
import 'datatables.net-responsive-dt';
import 'datatables.net-rowreorder-dt';
import 'datatables.net-select-dt';
import 'datatables.net-columncontrol-dt';

globalObj.DataTable = DataTable;

export default DataTable;
