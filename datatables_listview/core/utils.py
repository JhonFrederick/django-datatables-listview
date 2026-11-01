from collections import namedtuple
from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.exceptions import (
    FieldDoesNotExist,
    ImproperlyConfigured,
    ObjectDoesNotExist,
)
from django.templatetags.static import static

from datatables_listview.core.constants import (
    DEFAULT_BOOTSTRAP_VERSION,
    BOOTSTRAP_VERSIONS,
    DEFAULT_LANGUAGE_ALIASES,
    FALLBACK_LANGUAGE_FILE,
    DATATABLES_I18N_DIR,
)

Draw = namedtuple(
    "Draw", ["start", "end", "sort_column", "sort_order", "search", "draw", "filter"]
)


def is_ajax(request):
    """Check if the request was made via AJAX (XMLHttpRequest)."""
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def get_bootstrap_version():
    """
    Return the Bootstrap version ("4" or "5") configured in
    settings.DATATABLES_LISTVIEW_BOOTSTRAP_VERSION (default: "5").
    """
    version = str(
        getattr(
            settings,
            "DATATABLES_LISTVIEW_BOOTSTRAP_VERSION",
            DEFAULT_BOOTSTRAP_VERSION,
        )
    )
    if version not in BOOTSTRAP_VERSIONS:
        raise ImproperlyConfigured(
            "DATATABLES_LISTVIEW_BOOTSTRAP_VERSION must be one of %(versions)s, "
            "not %(value)r" % {"versions": BOOTSTRAP_VERSIONS, "value": version}
        )
    return version


def _normalize_language_code(language_code):
    return (language_code or "").replace("_", "-").lower()


def get_datatables_language_candidates(language_code):
    """
    Static paths of the DataTables language files to try, in order, for a
    Django language code (e.g. "es-mx" → es-MX, es, es-ES, en-GB).
    """
    lang, _, region = _normalize_language_code(language_code).partition("-")
    names = []
    if lang and region:
        names.append(f"{lang}-{region.upper()}")
    if lang:
        names.append(lang)
        if lang in DEFAULT_LANGUAGE_ALIASES:
            names.append(DEFAULT_LANGUAGE_ALIASES[lang])
        names.append(f"{lang}-{lang.upper()}")  # fr → fr-FR, de → de-DE...
    names.append(FALLBACK_LANGUAGE_FILE)
    return [f"{DATATABLES_I18N_DIR}/{name}.json" for name in dict.fromkeys(names)]


def get_datatables_language_url(language_code):
    """
    Static URL of the DataTables language file for a Django language code.

    1. settings.DATATABLES_LISTVIEW_LANGUAGE_FILES ({"es-mx": "app/es.json"}),
       by exact code and then by base language.
    2. The files shipped in datatables_listview/i18n/ (first one that exists).

    Returns None when no file is found (DataTables then uses its default).
    """
    code = _normalize_language_code(language_code)
    custom = {
        _normalize_language_code(key): path
        for key, path in getattr(
            settings, "DATATABLES_LISTVIEW_LANGUAGE_FILES", {}
        ).items()
    }
    for key in (code, code.split("-")[0]):
        if key in custom:
            return static(custom[key])

    for path in get_datatables_language_candidates(language_code):
        if finders.find(path):
            return static(path)
    return None


def get_field_name(field):
    """Get the string name of a field, supporting str and dict types."""
    if isinstance(field, str):
        return field
    elif isinstance(field, dict):
        try:
            return field["name"]
        except KeyError:
            raise AttributeError("field of dict type must have 'name' key")
    else:
        raise AttributeError("field item must be str or dict type")


def arrayfield_keys_to_values(keys, choices):
    """Convert array field keys to their display values using choices."""
    values = []
    if keys:
        if choices:
            choices_dict = dict(choices)
            for key in keys:
                if key in choices_dict:
                    values.append(choices_dict[key])
        else:
            values = keys
    return values


def create_column_defs_list(column_defs):
    """Create column definitions list suitable for DataTables."""
    column_defs_list = []
    for counter, column_def in enumerate(column_defs):
        if isinstance(column_def, str):
            column_defs_list.append(
                {
                    "title": column_def,
                    "targets": counter,
                    "orderable": 1,
                    "searchable": 1,
                }
            )
        elif isinstance(column_def, dict):
            column_def_copy = dict(column_def)
            column_def_copy["targets"] = counter
            column_defs_list.append(column_def_copy)
        else:
            column_defs_list.append(
                {
                    "title": str(column_def),
                    "targets": counter,
                    "orderable": 1,
                    "searchable": 1,
                }
            )
    return column_defs_list


def resolve_field_path(model, field_path):
    """
    Resolve a double-underscore field path (e.g. 'dog__name', 'profile__bio')
    against a Django model's _meta API.

    Returns a dict with metadata about the field path.
    """
    parts = field_path.split("__")
    current_model = model
    last_field = None
    is_relation = False
    is_many = False
    is_property = False

    for idx, part in enumerate(parts):
        try:
            field_obj = current_model._meta.get_field(part)
            last_field = field_obj

            if field_obj.is_relation:
                is_relation = True
                if getattr(field_obj, "many_to_many", False) or getattr(
                    field_obj, "one_to_many", False
                ):
                    is_many = True
                current_model = field_obj.related_model
            else:
                is_relation = False

        except FieldDoesNotExist:
            if hasattr(current_model, part):
                is_property = True
                last_field = getattr(current_model, part)
                is_relation = False
                break
            raise

    choices = getattr(last_field, "choices", None)

    return {
        "path": field_path,
        "parts": parts,
        "target_model": current_model,
        "target_field": last_field,
        "is_relation": is_relation,
        "is_many": is_many,
        "is_property": is_property,
        "choices": choices,
    }


def safe_get_attribute(obj, field_path):
    """
    Safely extract a value from an object given a field path (e.g. 'dog__name', 'cats__name').
    Gracefully handles None, ObjectDoesNotExist, OneToOne, ManyToMany, and callables.
    """
    if obj is None:
        return None

    parts = field_path.split("__")
    current = obj

    for idx, part in enumerate(parts):
        if current is None:
            return None

        # Check if current is a Django related manager (ManyToMany or OneToMany)
        if hasattr(current, "all") and hasattr(current, "values_list"):
            remaining = "__".join(parts[idx:])
            try:
                vals = list(current.values_list(remaining, flat=True))
                return ", ".join(str(v) for v in vals if v is not None)
            except Exception:
                return ", ".join(str(x) for x in current.all())

        try:
            val = getattr(current, part)
        except ObjectDoesNotExist:
            # Handles reverse OneToOne or ForeignKey where related object does not exist
            return None
        except AttributeError:
            return None

        # If it's a manager before we reached the end
        if hasattr(val, "all") and hasattr(val, "values_list"):
            remaining = parts[idx + 1 :]
            if remaining:
                subpath = "__".join(remaining)
                try:
                    vals = list(val.values_list(subpath, flat=True))
                    return ", ".join(str(v) for v in vals if v is not None)
                except Exception:
                    return ", ".join(str(x) for x in val.all())
            else:
                return ", ".join(str(x) for x in val.all())

        # If it's a method on a model or instance (not a manager)
        if callable(val):
            try:
                val = val()
            except TypeError:
                pass

        current = val

    return current
