from collections import namedtuple
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.db import models

Draw = namedtuple(
    "Draw", ["start", "end", "sort_column", "sort_order", "search", "draw", "filter"]
)


def is_ajax(request):
    """Check if the request was made via AJAX (XMLHttpRequest)."""
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


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
