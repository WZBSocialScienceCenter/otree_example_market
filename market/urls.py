"""
Custom URLs as explained in https://otree.readthedocs.io/en/latest/misc/django.html#adding-custom-pages-urls

This adds an URL for exporting all data (including the custom data models) as JSON.

July 2018, Markus Konrad <markus.konrad@wzb.eu>
"""

from django.conf.urls import url
from otree.urls import urlpatterns

#from . import data_export
from . import admin_extensions


patterns_conf = {
    'SessionData': (r"^SessionData/(?P<code>[a-z0-9]+)/$", admin_extensions.SessionDataExtension),
    'ExportApp': (r"^ExportApp/(?P<app_name>[\w.]+)/$", admin_extensions.ExportAppExtension),
}


urlpatterns = [pttrn for pttrn in urlpatterns if pttrn.name not in patterns_conf.keys()]

#urlpatterns.append(url(r'^dataexport/market/$', data_export.export_view_json))

for name, (pttrn, viewclass) in patterns_conf.items():
    urlpatterns.append(url(pttrn, viewclass.as_view(), name=name))
