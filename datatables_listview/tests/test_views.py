import pytest
from django.core.exceptions import ImproperlyConfigured

from datatables_listview.tests.models import TestPerson


class TestConfiguration:
    """Validations in __init__ when instantiating the view."""

    def test_missing_model_raises_improperly_configured(self, make_view):
        with pytest.raises(ImproperlyConfigured):
            make_view(model=None)

    def test_default_fields_exclude_to_many_and_reverse_relations(self, make_view):
        view = make_view()
        assert set(view.fields) == {"id", "name", "birth_date", "gender", "dog"}

    @pytest.mark.parametrize("index", [-1, 1])
    def test_invalid_default_column_order_index(self, make_view, index):
        with pytest.raises(ImproperlyConfigured):
            make_view(fields=["name"], default_column_order_index=index)

    def test_invalid_default_column_order_direction(self, make_view):
        with pytest.raises(ImproperlyConfigured):
            make_view(fields=["name"], default_column_order_direction="up")

    @pytest.mark.parametrize(
        "option",
        [
            {"option_label": "Ver"},
            {"option_label": "Ver", "option_url": "detalle"},
        ],
    )
    def test_options_list_requires_all_keys(self, make_view, option):
        with pytest.raises(ImproperlyConfigured):
            make_view(fields=["name"], options_list=[option])

    def test_show_options_depends_on_options_list(self, make_view):
        option = {"option_label": "Ver", "option_url": "detalle", "url_params": ["id"]}
        assert make_view(fields=["name"]).show_options is False
        assert make_view(fields=["name"], options_list=[option]).show_options is True


class TestFieldDefinitions:
    """Field definitions: field names, metadata and column definitions."""

    def test_field_names_accept_str_and_dict(self, make_view):
        view = make_view(
            fields=["name", {"name": "gender", "title": "Sex"}, "dog__name"]
        )
        assert view.get_field_names() == ["name", "gender", "dog__name"]

    @pytest.mark.parametrize("field", [{"title": "Sin name"}, 123])
    def test_invalid_field_item_raises(self, make_view, field):
        with pytest.raises(AttributeError):
            make_view(fields=[field])

    def test_column_defs_from_fields(self, make_view):
        view = make_view(fields=["name", {"name": "gender", "title": "Sex"}])
        defs = view.get_columns_defs()
        assert defs[0] == {
            "title": "name",
            "targets": 0,
            "orderable": 1,
            "searchable": 1,
        }
        assert defs[1]["title"] == "Sex"
        assert defs[1]["targets"] == 1

    def test_column_names_and_defs_override_fields(self, make_view):
        view = make_view(
            fields=["name", "dog__name"],
            column_names_and_defs=["Nombre", {"title": "Perro", "orderable": False}],
        )
        defs = view.get_columns_defs()
        assert [d["title"] for d in defs] == ["Nombre", "Perro"]
        assert defs[1]["orderable"] is False
        assert defs[1]["targets"] == 1

    @pytest.mark.parametrize(
        "path, is_relation, is_many, is_property",
        [
            ("name", False, False, False),
            ("dog", True, False, False),
            ("dog__name", False, False, False),
            ("profile__bio", False, False, False),
            ("cats__name", False, True, False),
            ("toys__toy_name", False, True, False),
            ("custom_status", False, False, True),
        ],
    )
    def test_field_metadata(self, make_view, path, is_relation, is_many, is_property):
        meta = make_view(fields=[path])._fields_definition[path]
        assert meta["is_relation"] is is_relation
        assert meta["is_many"] is is_many
        assert meta["is_property"] is is_property

    def test_choices_are_detected(self, make_view):
        meta = make_view(fields=["gender"])._fields_definition["gender"]
        assert dict(meta["choices"]) == {0: "MALE", 1: "FEMALE"}


class TestDrawParams:
    """Reading of the parameters that DataTables sent."""

    def test_parses_all_parameters(self, make_view, make_request):
        view = make_view(fields=["name", "gender", "dog__name"])
        request = make_request(
            start=10, length=20, column=2, direction="desc", search="Alice", draw=3
        )
        draw = view.get_draw_params(request)
        assert (draw.start, draw.end) == (10, 30)
        assert draw.sort_column == "dog__name"
        assert draw.sort_order == "desc"
        assert draw.search == "Alice"
        assert draw.draw == 3

    def test_defaults_when_no_parameters(self, rf, make_view):
        view = make_view(fields=["name", "gender"])
        draw = view.get_draw_params(rf.get("/"))
        assert (draw.start, draw.end) == (0, 10)
        assert draw.sort_column == "name"
        assert draw.sort_order == "asc"
        assert draw.search == ""
        assert draw.draw == 0
        assert draw.filter == {}

    def test_out_of_range_column_falls_back_to_first_field(
        self, make_view, make_request
    ):
        view = make_view(fields=["name", "gender"])
        draw = view.get_draw_params(make_request(column=99))
        assert draw.sort_column == "name"

    def test_negative_length_is_clamped(self, make_view, make_request):
        view = make_view(fields=["name"])
        draw = view.get_draw_params(make_request(start=4, length=-5))
        assert draw.end == draw.start == 4

    def test_column_filters_ignore_empty_values(self, make_view, make_request):
        view = make_view(fields=["name", "dog__name"])
        request = make_request(
            column_only=["dog__name", "name"], value_only=["Fido", ""]
        )
        draw = view.get_draw_params(request)
        assert draw.filter == {"dog__name": "Fido"}


class TestQueryset:
    """Building of the base queryset."""

    def test_get_queryset_returns_all_rows(self, data, make_view):
        assert make_view().get_queryset().count() == 3

    def test_custom_queryset_is_respected(self, data, make_view):
        view = make_view(queryset=TestPerson.objects.filter(gender=0))
        assert view.get_queryset().count() == 2

    def test_select_related_avoids_n_plus_one(
        self, data, make_view, django_assert_num_queries
    ):
        view = make_view(fields=["name", "dog__name", "profile__bio"])
        with django_assert_num_queries(1):
            rows = view.generate_rows(view.get_queryset())
        assert len(rows) == 3


class TestEvaluateData:
    """Extraction of the value of each field of an object."""

    def test_foreign_key_and_nested_lookups(self, data, make_view):
        view = make_view(fields=["name", "dog__name", "dog__age"])
        assert view.evaluate_data(data.person1, "dog__name")[0] == "Fido"
        assert view.evaluate_data(data.person1, "dog__age")[0] == 3

    def test_null_foreign_key_does_not_crash(self, data, make_view):
        view = make_view(fields=["name", "dog__name"])
        assert view.evaluate_data(data.person3, "dog__name")[0] is None

    def test_one_to_one(self, data, make_view):
        view = make_view(fields=["name", "profile__bio"])
        assert view.evaluate_data(data.person1, "profile__bio")[0] == "Alice bio"

    def test_missing_reverse_one_to_one_returns_none(self, data, make_view):
        view = make_view(fields=["name", "profile__bio"])
        assert view.evaluate_data(data.person2, "profile__bio")[0] is None

    @pytest.mark.parametrize(
        "path, expected",
        [
            ("cats__name", {"Whiskers", "Felix"}),  # many-to-many
            ("toys__toy_name", {"Ball", "Bone"}),  # FK inverso
        ],
    )
    def test_many_relations_are_joined_with_commas(
        self, data, make_view, path, expected
    ):
        view = make_view(fields=["name", path])
        value, _ = view.evaluate_data(data.person1, path)
        assert set(value.split(", ")) == expected

    def test_choices_show_label(self, data, make_view):
        view = make_view(fields=["name", "gender"])
        assert view.evaluate_data(data.person1, "gender")[0] == "FEMALE"

    def test_property(self, data, make_view):
        view = make_view(fields=["name", "custom_status"])
        assert view.evaluate_data(data.person1, "custom_status")[0] == "Status: Alice"


class TestSearch:
    """Global search (search[value])."""

    @pytest.mark.parametrize(
        "fields, extra, search, expected",
        [
            pytest.param(
                ["name", "dog__name"], {}, "Fido", "person1", id="ruta-anidada"
            ),
            pytest.param(["cats__name"], {}, "e", "person1", id="m2m-con-distinct"),
            pytest.param(
                ["name", "dog"],
                {"relation_search_fields": {"dog": ["name"]}},
                "Rex",
                "person2",
                id="relacion-explicita",
            ),
            pytest.param(
                ["name", "dog"], {}, "Rex", "person2", id="relacion-autodescubierta"
            ),
            pytest.param(
                ["name", "gender"], {}, "FEMALE", "person1", id="choices-por-etiqueta"
            ),
            pytest.param(["name"], {}, "alice", "person1", id="ignora-mayusculas"),
        ],
    )
    def test_filter_by_search_text(
        self, data, make_view, fields, extra, search, expected
    ):
        view = make_view(fields=fields, **extra)
        filtered = view.filter_by_search_text(TestPerson.objects.all(), search)
        assert filtered.count() == 1
        assert filtered.first() == getattr(data, expected)

    def test_split_search_matches_any_word(self, data, make_view):
        view = make_view(fields=["name", "dog__name"], split_search=" ")
        filtered = view.filter_by_search_text(TestPerson.objects.all(), "Alice Rex")
        assert set(filtered.values_list("pk", flat=True)) == {
            data.person1.pk,
            data.person2.pk,
        }

    def test_without_split_search_the_text_is_a_single_term(self, data, make_view):
        view = make_view(fields=["name", "dog__name"])
        filtered = view.filter_by_search_text(TestPerson.objects.all(), "Alice Rex")
        assert filtered.count() == 0

    def test_properties_are_ignored(self, data, make_view):
        view = make_view(fields=["name", "custom_status"])
        filtered = view.filter_by_search_text(TestPerson.objects.all(), "Status")
        assert filtered.count() == 0

    @pytest.mark.parametrize(
        "fields",
        [
            pytest.param(["name", "gender"], id="campos-normales-y-choices"),
            pytest.param(["gender"], id="solo-choices"),
            pytest.param(["custom_status"], id="solo-propiedades"),
            pytest.param(["gender", "custom_status"], id="choices-y-propiedades"),
        ],
    )
    def test_no_match_returns_nothing(self, data, make_view, fields):
        view = make_view(fields=fields)
        filtered = view.filter_by_search_text(TestPerson.objects.all(), "zzz")
        assert filtered.count() == 0

    def test_search_without_terms_applies_no_filter(self, data, make_view):
        view = make_view(fields=["name", "dog__name"], split_search=" ")
        filtered = view.filter_by_search_text(TestPerson.objects.all(), "   ")
        assert filtered.count() == 3


class TestGenerateData:
    """Complete cycle: search, order and pagination."""

    def test_full_cycle(self, data, make_view, make_request):
        view = make_view(fields=["name", "dog__name", "profile__bio", "custom_status"])
        result = view.generate_data(make_request())
        assert result["draw"] == 1
        assert result["recordsTotal"] == 3
        assert result["recordsFiltered"] == 3
        assert len(result["data"]) == 3
        first_row = result["data"][0]
        assert len(first_row) == 4
        assert first_row[0].startswith("<span>")

    def test_order_descending(self, data, make_view, make_request):
        view = make_view(fields=["name", "dog__name"])
        result = view.generate_data(make_request(direction="desc"))
        assert [row[0] for row in result["data"]] == [
            "<span>Charlie</span>",
            "<span>Bob</span>",
            "<span>Alice</span>",
        ]

    def test_pagination(self, data, make_view, make_request):
        view = make_view(fields=["name"])
        first = view.generate_data(make_request(start=0, length=2))
        second = view.generate_data(make_request(start=2, length=2))
        assert len(first["data"]) == 2
        assert second["data"] == [["<span>Charlie</span>"]]
        assert first["recordsTotal"] == first["recordsFiltered"] == 3

    def test_search_updates_records_filtered(self, data, make_view, make_request):
        view = make_view(fields=["name", "dog__name"])
        result = view.generate_data(make_request(search="Fido"))
        assert result["recordsTotal"] == 3
        assert result["recordsFiltered"] == 1
        assert len(result["data"]) == 1

    def test_search_without_matches_returns_empty_result(
        self, data, make_view, make_request
    ):
        # Solo choices: antes la búsqueda sin coincidencias devolvía todas las filas
        view = make_view(fields=["gender"])
        result = view.generate_data(make_request(search="zzz"))
        assert result["recordsTotal"] == 3
        assert result["recordsFiltered"] == 0
        assert result["data"] == []

    @pytest.mark.parametrize("path", ["custom_status", "cats__name"])
    def test_sorting_by_property_or_many_relation_does_not_fail(
        self, data, make_view, make_request, path
    ):
        view = make_view(fields=["name", path])
        result = view.generate_data(make_request(column=1))
        assert len(result["data"]) == 3
