from django.db import models


class TestCat(models.Model):
    __test__ = False
    name = models.CharField(max_length=30)
    hate_level = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class TestDog(models.Model):
    __test__ = False
    name = models.CharField(max_length=30)
    age = models.IntegerField(default=1)

    def __str__(self):
        return self.name


class TestPerson(models.Model):
    __test__ = False
    GENDERS = (
        (0, "MALE"),
        (1, "FEMALE"),
    )
    name = models.CharField(max_length=30)
    birth_date = models.DateField(auto_now_add=True)
    gender = models.IntegerField(choices=GENDERS, default=0)
    dog = models.ForeignKey(TestDog, on_delete=models.CASCADE, null=True, blank=True)
    cats = models.ManyToManyField(TestCat, blank=True)

    def __str__(self):
        return self.name

    @property
    def custom_status(self):
        return f"Status: {self.name}"


class TestProfile(models.Model):
    __test__ = False
    person = models.OneToOneField(
        TestPerson, on_delete=models.CASCADE, related_name="profile"
    )
    bio = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Profile of {self.person.name}"


class TestToy(models.Model):
    __test__ = False
    owner = models.ForeignKey(TestPerson, on_delete=models.CASCADE, related_name="toys")
    toy_name = models.CharField(max_length=50)

    def __str__(self):
        return self.toy_name
