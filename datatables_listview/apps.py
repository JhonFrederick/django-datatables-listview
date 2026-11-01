import os
from django.apps import AppConfig


class DatatablesListviewConfig(AppConfig):
    name = "datatables_listview"
    path = os.path.dirname(os.path.abspath(__file__))
    verbose_name = "Datatables Listview"
