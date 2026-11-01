from types import SimpleNamespace

import pytest

from datatables_listview.core.views import DatatablesListView
from datatables_listview.tests.models import (
    TestCat,
    TestDog,
    TestPerson,
    TestProfile,
    TestToy,
)


@pytest.fixture
def data(db):
    """3 people, 2 dogs, 2 cats, 1 profile and 2 toys."""
    dog1 = TestDog.objects.create(name="Fido", age=3)
    dog2 = TestDog.objects.create(name="Rex", age=5)
    cat1 = TestCat.objects.create(name="Whiskers", hate_level=2)
    cat2 = TestCat.objects.create(name="Felix", hate_level=5)

    person1 = TestPerson.objects.create(name="Alice", gender=1, dog=dog1)
    person1.cats.add(cat1, cat2)
    TestProfile.objects.create(person=person1, bio="Alice bio")
    TestToy.objects.create(owner=person1, toy_name="Ball")
    TestToy.objects.create(owner=person1, toy_name="Bone")

    # Bob has a dog but no profile; Charlie has no dog nor profile
    person2 = TestPerson.objects.create(name="Bob", gender=0, dog=dog2)
    person3 = TestPerson.objects.create(name="Charlie", gender=0, dog=None)

    return SimpleNamespace(person1=person1, person2=person2, person3=person3)


@pytest.fixture
def make_view():
    """Create and instance a subclase of DatatablesListView with the given attributes."""

    def _make(model=TestPerson, **attrs):
        cls = type("View", (DatatablesListView,), {"model": model, **attrs})
        return cls()

    return _make


@pytest.fixture
def make_request(rf):
    """Request GET with the parameters that DataTables sent (default values included)."""

    def _make(
        start=0, length=10, column=0, direction="asc", search="", draw=1, **extra
    ):
        params = {
            "start": start,
            "length": length,
            "order[0][column]": column,
            "order[0][dir]": direction,
            "search[value]": search,
            "draw": draw,
        }
        params.update(extra)
        return rf.get("/", params)

    return _make
