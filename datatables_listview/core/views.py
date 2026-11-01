from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q, CharField, TextField
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse

from datatables_listview.core.constants import DatatableOrderConstants
from datatables_listview.core.utils import (
    create_column_defs_list,
    get_field_name,
    is_ajax,
    resolve_field_path,
    safe_get_attribute,
    Draw,
)


class DatatablesListView:
    """
    View implementation for datatables_listview supporting nested lookups,
    OneToOne, ManyToOne, OneToMany, ManyToMany relations, and multi-framework styling.
    """

    model = None
    queryset = None
    fields = None
    options_list = []
    show_options = True
    show_options_permission = None
    perms_manager = None
    column_names_and_defs = None
    table_name = None
    show_buttons = False
    split_search = None
    option_render_template_name = "datatables_listview/url_rendering_tool.html"
    default_column_order_index = 0
    default_column_order_direction = DatatableOrderConstants.ASCENDING
    theme = "default"
    relation_search_fields = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fields = None
        self.show_options = bool(self.options_list) and self.show_options
        self.fields_data = {}
        self._fields_definition = {}

        if self.model is None:
            raise ImproperlyConfigured(
                "%(cls)s is missing a Model. Define %(cls)s.model"
                % {"cls": self.__class__.__name__}
            )

        self._validate_fields()
        self._define_fields()

        for option in self.options_list:
            for req_key in ("option_label", "option_url", "url_params"):
                if req_key not in option:
                    raise ImproperlyConfigured(
                        "%(cls)s options_list dicts must include '%(key)s'"
                        % {"cls": self.__class__.__name__, "key": req_key}
                    )

        if (
            self.default_column_order_index < 0
            or self.default_column_order_index > len(self.fields) - 1
        ):
            raise ImproperlyConfigured(
                "%(cls)s default_column_order_index value must be between 0 and %(max)s"
                % {
                    "cls": self.__class__.__name__,
                    "max": len(self.fields) - 1,
                }
            )

        if self.default_column_order_direction not in [
            DatatableOrderConstants.ASCENDING,
            DatatableOrderConstants.DESCENDING,
        ]:
            raise ImproperlyConfigured(
                "%(cls)s default_column_order_direction value must be 'asc' or 'desc'"
                % {"cls": self.__class__.__name__}
            )

    def _validate_fields(self):
        """Validate defined fields and extract their metadata definitions."""
        if self.fields:
            for field in self.fields:
                field_name = get_field_name(field)
                try:
                    meta = resolve_field_path(self.model, field_name)
                    self._fields_definition[field_name] = meta
                except Exception:
                    # Properties, methods, or non-model fields
                    self._fields_definition[field_name] = {
                        "path": field_name,
                        "is_property": True,
                        "is_relation": False,
                        "is_many": False,
                        "choices": None,
                    }

    def _define_fields(self):
        """Default fields from model if not explicitly configured."""
        if not self.fields:
            self.fields = []
            for field_obj in self.model._meta.get_fields():
                if not field_obj.is_relation or getattr(
                    field_obj, "many_to_one", False
                ):
                    self.fields.append(field_obj.name)
                    self._fields_definition[field_obj.name] = resolve_field_path(
                        self.model, field_obj.name
                    )

    def _get_relation_lookup_fields(self, field_name, meta):
        """
        Determine which fields of a related model should be searched.
        Priority:
        1. self.relation_search_fields[field_name]
        2. related_model.LOOKUP_FIELDS (if defined)
        3. Autodiscovery of CharField and TextField on the related model
        """
        if field_name in self.relation_search_fields:
            return self.relation_search_fields[field_name]

        target_model = meta.get("target_model")
        if target_model:
            if hasattr(target_model, "LOOKUP_FIELDS"):
                return target_model.LOOKUP_FIELDS

            # Autodiscover text fields
            discovered = [
                f.name
                for f in target_model._meta.get_fields()
                if isinstance(f, (CharField, TextField))
            ]
            if discovered:
                return discovered

        return []

    def get_search_words(self, search_text):
        """Split the search text into non-empty terms."""
        if self.split_search is None:
            words = [search_text]
        else:
            words = search_text.split(self.split_search)
        return [word for word in words if word]

    def generate_q_objects_by_fields_and_words(self, search_text):
        """
        Generate Q objects across fields, supporting nested relations, choices,
        and configurable lookups.

        Returns an empty Q when no field can match any of the terms.
        """
        q = Q()
        words = self.get_search_words(search_text)

        for field_item in self.fields:
            field_name = get_field_name(field_item)
            meta = self._fields_definition.get(field_name, {})

            if meta.get("is_property"):
                # Cannot query properties directly via SQL
                continue

            for word in words:
                # If the field is a direct relation (e.g. 'dog' or 'cats') without subpath
                if meta.get("is_relation") and "__" not in field_name:
                    lookup_fields = self._get_relation_lookup_fields(field_name, meta)
                    for lookup in lookup_fields:
                        lookup_path = f"{field_name}__{lookup}"
                        q.add(Q(**{f"{lookup_path}__icontains": word}), Q.OR)

                # If field has choices
                elif meta.get("choices"):
                    field_choices = meta["choices"]
                    matching_keys = [
                        k
                        for k, label in field_choices
                        if word.lower() in str(label).lower()
                    ]
                    if matching_keys:
                        q.add(Q(**{f"{field_name}__in": matching_keys}), Q.OR)

                # Direct field or nested field (e.g. 'name', 'dog__name', 'cats__name')
                else:
                    q.add(Q(**{f"{field_name}__icontains": word}), Q.OR)

        return q

    def get_options_list(self):
        return self.options_list

    def get_queryset(self):
        """
        Get or initialize queryset with automated select_related and prefetch_related
        to eliminate N+1 queries.
        """
        if self.queryset is None:
            self.queryset = self.model._default_manager.all()

        qs = self.queryset
        select_related = []
        prefetch_related = []

        for field_item in self.fields:
            field_name = get_field_name(field_item)
            meta = self._fields_definition.get(field_name)
            if meta and not meta.get("is_property"):
                parts = meta["path"].split("__")
                if meta.get("is_many"):
                    prefetch_related.append(parts[0])
                elif len(parts) > 1 or meta.get("is_relation"):
                    select_related.append(parts[0])

        if select_related:
            try:
                qs = qs.select_related(*set(select_related))
            except Exception:
                pass

        if prefetch_related:
            try:
                qs = qs.prefetch_related(*set(prefetch_related))
            except Exception:
                pass

        return qs

    def get_field_names(self):
        return [get_field_name(f) for f in self.fields]

    def get_columns_defs(self):
        if self.column_names_and_defs:
            return create_column_defs_list(self.column_names_and_defs)
        return create_column_defs_list(self.fields)

    def render_option(self, option_conf, params, obj):
        context = {
            "name": option_conf["option_label"],
            "url": reverse(option_conf["option_url"], args=params),
            "icon": option_conf.get("icon"),
            "confirm_modal": option_conf.get("confirm_modal"),
            "new_tab": option_conf.get("new_tab"),
        }
        return self.option_render_template_name, context

    def get_draw_params(self, request):
        start = int(request.GET.get("start", 0))
        length = max(int(request.GET.get("length", 10)), 0)
        end = start + length

        filter_dict = {}
        filter_params = request.GET.getlist("column_only")
        filter_values = request.GET.getlist("value_only")
        if filter_params:
            for param, value in zip(filter_params, filter_values):
                if bool(value):
                    filter_dict[param] = value

        column_idx = int(request.GET.get("order[0][column]", 0))
        field_names = self.get_field_names()
        sort_column = (
            field_names[column_idx] if column_idx < len(field_names) else field_names[0]
        )

        sort_order = request.GET.get("order[0][dir]", "asc")
        search = request.GET.get("search[value]", "")
        draw = int(request.GET.get("draw", 0))

        return Draw(start, end, sort_column, sort_order, search, draw, filter_dict)

    def filter_by_search_text(self, queryset, search_text):
        """
        Filter queryset by search text, applying distinct when joining collections.

        If the text has terms but no field can match them (no match in choices
        labels, only properties, etc.), nothing is returned. A text without
        terms (e.g. only separators) applies no filter.
        """
        if not self.get_search_words(search_text):
            return queryset

        q_objects = self.generate_q_objects_by_fields_and_words(search_text)
        if not q_objects:
            return queryset.none()

        qs = queryset.filter(q_objects)

        # Apply distinct if any relation involves multiple values (M2M or reverse FK)
        needs_distinct = any(
            meta.get("is_many") for meta in self._fields_definition.values()
        )
        if needs_distinct:
            qs = qs.distinct()

        return qs

    def filter_by_draw_params(self, queryset, draw_params):
        """Filter, sort, and slice the queryset according to DataTables draw parameters."""
        sort_order = "-" if draw_params.sort_order == "desc" else ""
        meta = self._fields_definition.get(draw_params.sort_column)

        # Only apply database-level order_by if not a property and not a ManyToMany
        if meta and not meta.get("is_property") and not meta.get("is_many"):
            sort_criteria = f"{sort_order}{draw_params.sort_column}"
            try:
                ordered_qs = queryset.order_by(sort_criteria)
            except Exception:
                ordered_qs = queryset
        else:
            ordered_qs = queryset

        filtered_qs = ordered_qs
        if draw_params.filter:
            filtered_qs = filtered_qs.filter(**draw_params.filter)

        return (
            filtered_qs.count(),
            filtered_qs[draw_params.start : draw_params.end],
        )

    def generate_rows(self, queryset):
        return [self.get_obj_data(obj) for obj in queryset]

    def generate_rows_with_options(self, queryset):
        data = []
        for obj in queryset:
            row = self.get_obj_data(obj)
            options = render_to_string(
                "datatables_listview/options_list_rendering_tool.html",
                {"urls": self.get_rendered_urls(obj)},
            )
            row.append(options)
            data.append(row)
        return data

    def get_obj_data(self, obj):
        row = []
        for field in self.fields:
            value, meta = self.evaluate_data(obj, field)
            row.append(self.get_rendered_html_value(meta, value, obj))
        return row

    def get_url_param(self, field, obj):
        value, _ = self.evaluate_data(obj, field)
        return value

    def get_rendered_urls(self, obj):
        rendered_urls = []
        for option_conf in self.get_options_list():
            permissions = option_conf.get("permissions")
            conditions = option_conf.get("conditions")

            if self.evaluate_conditions(obj, permissions, conditions):
                params = [
                    self.get_url_param(param, obj)
                    for param in option_conf.get("url_params", [])
                ]
                template_name, context = self.render_option(
                    option_conf=option_conf, params=params, obj=obj
                )
                rendered_urls.append(
                    render_to_string(template_name=template_name, context=context)
                )
        return rendered_urls

    def evaluate_conditions(self, obj, permissions, conditions):
        if permissions:
            perm_manager = (
                getattr(self.request.user, self.perms_manager)
                if self.perms_manager
                else self.request.user
            )
            for permission in permissions:
                perm = getattr(perm_manager, permission, None)
                if callable(perm):
                    perm = perm()
                if not perm:
                    return False

        if conditions:
            for condition in conditions:
                field_name = condition["field"]
                field_value, _ = self.evaluate_data(obj, field_name)
                condition_func = condition["condition_func"]
                if not condition_func(field_value, condition["condition_values"], obj):
                    return False
        return True

    def evaluate_data(self, obj, field):
        """
        Safely extract data for a field or nested relation path from an object instance.
        """
        field_name = get_field_name(field)
        key = f"{field_name}-{getattr(obj, 'pk', id(obj))}"

        if key in self.fields_data:
            return self.fields_data[key], self._fields_definition.get(field_name)

        meta = self._fields_definition.get(field_name, {})
        value = safe_get_attribute(obj, field_name)

        # Handle choices display
        if meta and meta.get("choices") and value is not None:
            choices_dict = dict(meta["choices"])
            value = choices_dict.get(value, value)

        self.fields_data[key] = value
        return value, meta

    def get_rendered_html_value(self, field_def, value, obj):
        if value is None:
            return "<span></span>"
        return f"<span>{value}</span>"

    def generate_data(self, request):
        draw_params = self.get_draw_params(request)
        queryset = self.get_queryset()
        total_count = queryset.count()

        if draw_params.search:
            queryset = self.filter_by_search_text(queryset, draw_params.search)

        filtered_count, paginated_qs = self.filter_by_draw_params(queryset, draw_params)

        if self.get_options_list():
            generated_rows = self.generate_rows_with_options(paginated_qs)
        else:
            generated_rows = self.generate_rows(paginated_qs)

        return {
            "draw": draw_params.draw,
            "recordsTotal": total_count,
            "recordsFiltered": filtered_count,
            "data": generated_rows,
        }

    def get(self, request, *args, **kwargs):
        if is_ajax(request):
            return JsonResponse(self.generate_data(request))
        return super().get(request, *args, **kwargs)

    def has_user_permission(self, permission):
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            manager = getattr(user, self.perms_manager) if self.perms_manager else user
            return getattr(manager, permission, False)
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_options"] = self.show_options
        if self.show_options_permission:
            context["show_options"] = self.has_user_permission(
                self.show_options_permission
            )

        context["column_defs"] = self.get_columns_defs()
        context["table_name"] = self.table_name
        context["show_buttons"] = self.show_buttons
        context["datatables_theme"] = getattr(self, "theme", "default")
        context["default_column_order"] = [
            self.default_column_order_index,
            self.default_column_order_direction,
        ]
        return context
