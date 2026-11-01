from types import SimpleNamespace

import pytest
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured

from datatables_listview.core.utils import (
    Draw,
    arrayfield_keys_to_values,
    create_column_defs_list,
    get_bootstrap_version,
    get_datatables_language_candidates,
    get_datatables_language_url,
    get_field_name,
    is_ajax,
    resolve_field_path,
    safe_get_attribute,
)
from datatables_listview.tests.models import (
    TestCat,
    TestDog,
    TestPerson,
    TestProfile,
    TestToy,
)

I18N = "datatables_listview/i18n"


class TestDraw:
    def test_fields_keep_their_order(self):
        assert Draw._fields == (
            "start",
            "end",
            "sort_column",
            "sort_order",
            "search",
            "draw",
            "filter",
        )


class TestGetBootstrapVersion:
    SETTING = "DATATABLES_LISTVIEW_BOOTSTRAP_VERSION"

    def test_default_is_5_when_not_configured(self, settings):
        if hasattr(settings, self.SETTING):
            delattr(settings, self.SETTING)
        assert get_bootstrap_version() == "5"

    @pytest.mark.parametrize(
        "value, expected", [("4", "4"), (4, "4"), ("5", "5"), (5, "5")]
    )
    def test_valid_values_are_returned_as_str(self, settings, value, expected):
        setattr(settings, self.SETTING, value)
        assert get_bootstrap_version() == expected

    @pytest.mark.parametrize("value", ["3", "6", "bootstrap5", "", None])
    def test_invalid_values_raise(self, settings, value):
        setattr(settings, self.SETTING, value)
        with pytest.raises(ImproperlyConfigured):
            get_bootstrap_version()


class TestGetDatatablesLanguageCandidates:
    """Order of the language files that are tested for a Django code."""

    @pytest.mark.parametrize(
        "code, expected",
        [
            ("es-mx", ["es-MX", "es", "es-ES", "en-GB"]),
            ("es", ["es", "es-MX", "es-ES", "en-GB"]),
            ("en-us", ["en-US", "en", "en-GB", "en-EN"]),
            ("fr", ["fr", "fr-FR", "en-GB"]),
            ("pt_BR", ["pt-BR", "pt", "pt-PT", "en-GB"]),
            ("", ["en-GB"]),
            (None, ["en-GB"]),
        ],
    )
    def test_candidates(self, code, expected):
        assert get_datatables_language_candidates(code) == [
            f"{I18N}/{name}.json" for name in expected
        ]


class TestGetDatatablesLanguageUrl:
    """Real resolution against a temporary static directory."""

    @pytest.fixture
    def add_i18n(self, tmp_path, settings):
        settings.STATIC_URL = "/static/"
        settings.STATICFILES_DIRS = [str(tmp_path)]
        settings.STATICFILES_FINDERS = [
            "django.contrib.staticfiles.finders.FileSystemFinder"
        ]
        folder = tmp_path / I18N
        folder.mkdir(parents=True)

        def _add(*names):
            for name in names:
                (folder / f"{name}.json").write_text("{}")

        return _add

    @staticmethod
    def url(name):
        return f"/static/{I18N}/{name}.json"

    def test_exact_region(self, add_i18n):
        add_i18n("es-MX", "es-ES")
        assert get_datatables_language_url("es-es") == self.url("es-ES")

    def test_language_only_uses_the_default_alias(self, add_i18n):
        add_i18n("es-MX", "es-ES")
        assert get_datatables_language_url("es") == self.url("es-MX")

    def test_region_without_file_falls_back_to_the_language(self, add_i18n):
        add_i18n("en-GB")
        assert get_datatables_language_url("en-us") == self.url("en-GB")

    def test_language_with_same_region_code(self, add_i18n):
        add_i18n("fr-FR", "en-GB")
        assert get_datatables_language_url("fr") == self.url("fr-FR")

    @pytest.mark.parametrize("code", ["xx", "", None])
    def test_unknown_language_falls_back_to_english(self, add_i18n, code):
        add_i18n("en-GB")
        assert get_datatables_language_url(code) == self.url("en-GB")

    def test_returns_none_when_there_are_no_files(self, add_i18n):
        assert get_datatables_language_url("es") is None

    def test_custom_file_by_exact_code_wins(self, add_i18n, settings):
        add_i18n("es-MX")
        settings.DATATABLES_LISTVIEW_LANGUAGE_FILES = {
            "es-mx": "proyecto/es-mx.json",
            "es": "proyecto/es.json",
        }
        assert get_datatables_language_url("es-MX") == "/static/proyecto/es-mx.json"

    def test_custom_file_by_base_language(self, add_i18n, settings):
        add_i18n("es-MX")
        settings.DATATABLES_LISTVIEW_LANGUAGE_FILES = {"es": "proyecto/es.json"}
        assert get_datatables_language_url("es-ar") == "/static/proyecto/es.json"

    def test_custom_keys_are_normalized(self, add_i18n, settings):
        settings.DATATABLES_LISTVIEW_LANGUAGE_FILES = {"PT_BR": "proyecto/pt.json"}
        assert get_datatables_language_url("pt-br") == "/static/proyecto/pt.json"


class TestIsAjax:
    def test_true_with_xmlhttprequest_header(self, rf):
        request = rf.get("/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        assert is_ajax(request) is True

    def test_false_without_header(self, rf):
        assert is_ajax(rf.get("/")) is False

    def test_false_with_other_header_value(self, rf):
        request = rf.get("/", HTTP_X_REQUESTED_WITH="fetch")
        assert is_ajax(request) is False


class TestGetFieldName:
    def test_str_is_returned_as_is(self):
        assert get_field_name("dog__name") == "dog__name"

    def test_dict_returns_name_key(self):
        assert get_field_name({"name": "gender", "title": "Sex"}) == "gender"

    def test_dict_without_name_raises(self):
        with pytest.raises(AttributeError, match="'name'"):
            get_field_name({"title": "Sex"})

    @pytest.mark.parametrize("field", [123, None, ["name"], ("name",)])
    def test_other_types_raise(self, field):
        with pytest.raises(AttributeError):
            get_field_name(field)


class TestArrayfieldKeysToValues:
    CHOICES = [("a", "Alpha"), ("b", "Beta")]

    def test_keys_are_converted_to_labels(self):
        assert arrayfield_keys_to_values(["a", "b"], self.CHOICES) == ["Alpha", "Beta"]

    def test_unknown_keys_are_skipped(self):
        assert arrayfield_keys_to_values(["a", "z"], self.CHOICES) == ["Alpha"]

    def test_without_choices_keys_are_returned(self):
        assert arrayfield_keys_to_values(["a", "b"], None) == ["a", "b"]

    @pytest.mark.parametrize("keys", [None, []])
    @pytest.mark.parametrize("choices", [None, CHOICES])
    def test_empty_keys_return_empty_list(self, keys, choices):
        assert arrayfield_keys_to_values(keys, choices) == []


class TestCreateColumnDefsList:
    def test_empty_list(self):
        assert create_column_defs_list([]) == []

    def test_str_column(self):
        assert create_column_defs_list(["Nombre"]) == [
            {"title": "Nombre", "targets": 0, "orderable": 1, "searchable": 1}
        ]

    def test_dict_column_keeps_its_options_and_gets_target(self):
        defs = create_column_defs_list(
            ["Nombre", {"title": "Perro", "orderable": False}]
        )
        assert defs[0] == {
            "title": "Nombre",
            "targets": 0,
            "orderable": 1,
            "searchable": 1,
        }
        assert defs[1] == {"title": "Perro", "orderable": False, "targets": 1}

    def test_dict_target_is_overwritten_by_position(self):
        defs = create_column_defs_list([{"title": "X", "targets": 99}])
        assert defs[0]["targets"] == 0

    def test_input_dict_is_not_mutated(self):
        original = {"title": "Perro"}
        create_column_defs_list([original])
        assert original == {"title": "Perro"}

    def test_other_types_use_str_as_title(self):
        defs = create_column_defs_list([5])
        assert defs == [{"title": "5", "targets": 0, "orderable": 1, "searchable": 1}]

    def test_targets_follow_the_position(self):
        defs = create_column_defs_list(["a", {"title": "b"}, 3])
        assert [d["targets"] for d in defs] == [0, 1, 2]


class TestResolveFieldPath:
    """Use only the API's _meta functions; no database access."""

    @pytest.mark.parametrize(
        "path, target_model, is_relation, is_many",
        [
            ("name", TestPerson, False, False),
            ("dog", TestDog, True, False),
            ("dog__name", TestDog, False, False),
            ("profile__bio", TestProfile, False, False),  # Reverse OneToOne
            ("cats", TestCat, True, True),
            ("cats__name", TestCat, False, True),
            ("toys__toy_name", TestToy, False, True),  # Reverse FK
        ],
    )
    def test_model_fields_and_relations(self, path, target_model, is_relation, is_many):
        meta = resolve_field_path(TestPerson, path)
        assert meta["path"] == path
        assert meta["parts"] == path.split("__")
        assert meta["target_model"] is target_model
        assert meta["is_relation"] is is_relation
        assert meta["is_many"] is is_many
        assert meta["is_property"] is False

    def test_target_field_is_the_last_field_of_the_path(self):
        meta = resolve_field_path(TestPerson, "dog__name")
        assert meta["target_field"] is TestDog._meta.get_field("name")

    def test_choices_are_returned(self):
        meta = resolve_field_path(TestPerson, "gender")
        assert dict(meta["choices"]) == {0: "MALE", 1: "FEMALE"}

    def test_fields_without_choices_return_none(self):
        assert resolve_field_path(TestPerson, "name")["choices"] is None

    def test_property_is_detected(self):
        meta = resolve_field_path(TestPerson, "custom_status")
        assert meta["is_property"] is True
        assert meta["is_relation"] is False
        assert isinstance(meta["target_field"], property)
        assert meta["target_model"] is TestPerson
        assert meta["choices"] is None

    @pytest.mark.parametrize("path", ["nope", "dog__nope"])
    def test_unknown_field_raises(self, path):
        with pytest.raises(FieldDoesNotExist):
            resolve_field_path(TestPerson, path)


class TestSafeGetAttribute:
    def test_none_object_returns_none(self):
        assert safe_get_attribute(None, "name") is None

    def test_simple_attribute(self, data):
        assert safe_get_attribute(data.person1, "name") == "Alice"

    def test_value_keeps_its_type(self, data):
        assert safe_get_attribute(data.person1, "dog__age") == 3

    def test_foreign_key_path(self, data):
        assert safe_get_attribute(data.person1, "dog__name") == "Fido"

    def test_null_foreign_key_returns_none(self, data):
        assert safe_get_attribute(data.person3, "dog__name") is None

    def test_none_in_the_middle_of_the_path_returns_none(self):
        assert safe_get_attribute(SimpleNamespace(a=None), "a__b") is None

    def test_reverse_one_to_one(self, data):
        assert safe_get_attribute(data.person1, "profile__bio") == "Alice bio"

    def test_missing_reverse_one_to_one_returns_none(self, data):
        assert safe_get_attribute(data.person2, "profile__bio") is None

    def test_missing_attribute_returns_none(self, data):
        assert safe_get_attribute(data.person1, "nope") is None

    def test_property(self, data):
        assert safe_get_attribute(data.person1, "custom_status") == "Status: Alice"

    def test_callable_is_called(self, data):
        assert safe_get_attribute(data.person1, "get_gender_display") == "FEMALE"

    def test_callable_without_default_args_is_called(self):
        assert safe_get_attribute(SimpleNamespace(f=lambda: 7), "f") == 7

    def test_callable_that_needs_arguments_is_returned_as_is(self):
        def needs_arg(x):
            return x

        assert safe_get_attribute(SimpleNamespace(f=needs_arg), "f") is needs_arg

    @pytest.mark.parametrize(
        "path, expected",
        [
            ("cats__name", {"Whiskers", "Felix"}),  # many-to-many with subpath
            ("cats", {"Whiskers", "Felix"}),  # many-to-many without subpath: str()
            ("toys__toy_name", {"Ball", "Bone"}),  # Reverse FK
            ("toys", {"Ball", "Bone"}),
        ],
    )
    def test_many_relations_are_joined_with_commas(self, data, path, expected):
        value = safe_get_attribute(data.person1, path)
        assert set(value.split(", ")) == expected

    def test_many_relation_without_items_returns_empty_string(self, data):
        assert safe_get_attribute(data.person2, "cats__name") == ""

    def test_invalid_subpath_falls_back_to_str_of_items(self, data):
        value = safe_get_attribute(data.person1, "cats__nope")
        assert set(value.split(", ")) == {"Whiskers", "Felix"}

    def test_queryset_attribute_with_subpath(self, data):
        obj = SimpleNamespace(items=TestCat.objects.all())
        value = safe_get_attribute(obj, "items__name")
        assert set(value.split(", ")) == {"Whiskers", "Felix"}

    def test_queryset_as_the_object_itself(self, data):
        value = safe_get_attribute(TestCat.objects.all(), "name")
        assert set(value.split(", ")) == {"Whiskers", "Felix"}
