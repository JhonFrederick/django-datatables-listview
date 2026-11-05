# django-datatables-listview

A DataTables Django server-side scripting implementation.

## Features

- Server-side processing with pagination, sorting, and multi-field search.
- Pre-bundled, minified DataTables assets updated to the latest versions:
  - **DataTables Core 3.1.5**
  - **Buttons 4.1.3** (Copy, CSV, Excel, PDF, Print, ColVis) with JSZip (3.10.2) and pdfmake (0.3.13)
  - **Responsive 4.1.1**
  - **RowReorder 2.1.1**
  - **ColReorder 3.1.2**
  - **Select 4.1.1**
- Multi-framework styling compatibility:
  - **Default DataTables** styling
  - **Bootstrap 4** styling (`bootstrap4` / `bs4`)
  - **Bootstrap 5** styling (`bootstrap5` / `bs5`)

---

## Installation (for Django applications)

End users installing this package only need standard Python requirements. **Node.js is NOT required.**

```bash
pip install django-datatables-listview
```

Add `datatables_listview` to your `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    ...,
    'datatables_listview',
]
```

---

## Usage in Templates

### 1. Default DataTables Styling

Include CSS in your `<head>`:
```html
{% include "datatables_listview/css.html" %}
```

Include JS before `</body>`:
```html
{% include "datatables_listview/js.html" %}
```

---

### 2. Switching Themes: Bootstrap 4 or Bootstrap 5

You can choose the styling framework in two ways:

#### Option A: Set the `theme` in your Django View

In your view, specify `theme = "bootstrap4"` or `theme = "bootstrap5"`:

```python
from datatables_listview.core.views import DatatablesListView

class MyBootstrap4ListView(DatatablesListView):
    model = MyModel
    theme = "bootstrap4"  # or "bs4"

class MyBootstrap5ListView(DatatablesListView):
    model = MyModel
    theme = "bootstrap5"  # or "bs5"
```

The standard `css.html` and `js.html` templates automatically inspect `datatables_theme` and load the respective bundle.

#### Option B: Use dedicated template partials

- **Bootstrap 4:**
  ```html
  {% include "datatables_listview/css_bs4.html" %}
  {% include "datatables_listview/js_bs4.html" %}
  ```

- **Bootstrap 5:**
  ```html
  {% include "datatables_listview/css_bs5.html" %}
  {% include "datatables_listview/js_bs5.html" %}
  ```

---

## Development & Asset Management (NPM)

For repository maintainers wishing to update or re-bundle the static assets:

### Prerequisites

- Node.js (>= 18)
- npm (>= 9)

### Installing Frontend Dependencies

```bash
npm install
```

### Rebuilding Static Files

```bash
npm run build
```

This compiles and minifies all 3 target bundles to `datatables_listview/static/datatables_listview/`:
- `datatables.min.js` & `datatables.min.css` (Default styling)
- `datatables.bs4.min.js` & `datatables.bs4.min.css` (Bootstrap 4)
- `datatables.bs5.min.js` & `datatables.bs5.min.css` (Bootstrap 5)

### Updating to the Latest DataTables Versions

To update all npm packages to their latest versions and recompile static assets:

```bash
npm run update-static
```
