"""
Custom URLs as explained in https://otree.readthedocs.io/en/latest/misc/django.html#adding-custom-pages-urls

This adds an URL for exporting all data (including the custom data models) as JSON.

July 2018, Markus Konrad <markus.konrad@wzb.eu>
"""

from django.conf.urls import url
from otree.urls import urlpatterns

from . import data_export
from . import admin_extensions


urlpatterns = [pttrn for pttrn in urlpatterns if pttrn.name != 'SessionData']

urlpatterns.append(url(r'^dataexport/market/$', data_export.export_view_json))
urlpatterns.append(url(r"^SessionData/(?P<code>[a-z0-9]+)/$", admin_extensions.SessionDataExtension.as_view(), name='SessionData'))
