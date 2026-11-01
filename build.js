const esbuild = require('esbuild');
const path = require('path');
const fs = require('fs');

const banner = `/**
 * Combined DataTables bundle for django-datatables-listview
 * Generated via npm & esbuild
 * To update dependencies: npm update && npm run build
 */`;

const externalJqueryPlugin = {
  name: 'external-jquery',
  setup(build) {
    build.onResolve({ filter: /^jquery$/ }, () => ({
      path: 'jquery',
      namespace: 'external-global',
    }));
    build.onLoad({ filter: /.*/, namespace: 'external-global' }, () => ({
      contents: `
        const $ = typeof window !== 'undefined' ? (window.jQuery || window.$) : (typeof globalThis !== 'undefined' ? (globalThis.jQuery || globalThis.$) : {});
        module.exports = $;
      `,
      loader: 'js',
    }));
  },
};

async function build() {
  const outJsDir = path.resolve(__dirname, 'datatables_listview/static/datatables_listview/js');
  const outCssDir = path.resolve(__dirname, 'datatables_listview/static/datatables_listview/css');
  const outI18nDir = path.resolve(__dirname, 'datatables_listview/static/datatables_listview/i18n');
  const i18nSrcDir = path.resolve(__dirname, 'node_modules/datatables.net-plugins/i18n');

  if (!fs.existsSync(outJsDir)) fs.mkdirSync(outJsDir, { recursive: true });
  if (!fs.existsSync(outCssDir)) fs.mkdirSync(outCssDir, { recursive: true });
  if (!fs.existsSync(outI18nDir)) fs.mkdirSync(outI18nDir, { recursive: true });

  console.log('Building DataTables bundles...');

  // 1. Default DataTables Bundle
  await esbuild.build({
    entryPoints: [path.resolve(__dirname, 'src/bundle-dt.js')],
    outfile: path.join(outJsDir, 'datatables.min.js'),
    bundle: true,
    minify: true,
    sourcemap: false,
    format: 'iife',
    banner: { js: banner },
    plugins: [externalJqueryPlugin],
    target: ['es2018'],
  });
  console.log('✔ Generated: datatables.min.js');

  await esbuild.build({
    entryPoints: [path.resolve(__dirname, 'src/bundle-dt.css')],
    outfile: path.join(outCssDir, 'datatables.min.css'),
    bundle: true,
    minify: true,
    sourcemap: false,
    banner: { css: banner },
  });
  console.log('✔ Generated: datatables.min.css');

  // 2. Bootstrap 4 DataTables Bundle
  await esbuild.build({
    entryPoints: [path.resolve(__dirname, 'src/bundle-bs4.js')],
    outfile: path.join(outJsDir, 'datatables.bs4.min.js'),
    bundle: true,
    minify: true,
    sourcemap: false,
    format: 'iife',
    banner: { js: banner },
    plugins: [externalJqueryPlugin],
    target: ['es2018'],
  });
  console.log('✔ Generated: datatables.bs4.min.js');

  await esbuild.build({
    entryPoints: [path.resolve(__dirname, 'src/bundle-bs4.css')],
    outfile: path.join(outCssDir, 'datatables.bs4.min.css'),
    bundle: true,
    minify: true,
    sourcemap: false,
    banner: { css: banner },
  });
  console.log('✔ Generated: datatables.bs4.min.css');

  // 3. Bootstrap 5 DataTables Bundle
  await esbuild.build({
    entryPoints: [path.resolve(__dirname, 'src/bundle-bs5.js')],
    outfile: path.join(outJsDir, 'datatables.bs5.min.js'),
    bundle: true,
    minify: true,
    sourcemap: false,
    format: 'iife',
    banner: { js: banner },
    plugins: [externalJqueryPlugin],
    target: ['es2018'],
  });
  console.log('✔ Generated: datatables.bs5.min.js');

  await esbuild.build({
    entryPoints: [path.resolve(__dirname, 'src/bundle-bs5.css')],
    outfile: path.join(outCssDir, 'datatables.bs5.min.css'),
    bundle: true,
    minify: true,
    sourcemap: false,
    banner: { css: banner },
  });
  console.log('✔ Generated: datatables.bs5.min.css');

  // 4. DataTables language files (datatables.net-plugins) -> static/i18n
  if (!fs.existsSync(i18nSrcDir)) {
    throw new Error(
      `Missing ${i18nSrcDir}. Run: npm install --save-dev datatables.net-plugins`
    );
  }
  const i18nFiles = fs.readdirSync(i18nSrcDir).filter((file) => file.endsWith('.json'));
  for (const file of i18nFiles) {
    fs.copyFileSync(path.join(i18nSrcDir, file), path.join(outI18nDir, file));
  }
  console.log(`✔ Copied: ${i18nFiles.length} i18n language files`);

  console.log('All static assets compiled successfully!');
}

build().catch((err) => {
  console.error(err);
  process.exit(1);
});