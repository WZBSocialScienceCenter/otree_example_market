"""
Custom URLs as explained in https://otree.readthedocs.io/en/latest/misc/django.html#adding-custom-pages-urls

This adds an URL for exporting all data (including the custom data models) as JSON.
"""

from django.conf.urls import url
from otree.urls import urlpatterns

from . import data_export


urlpatterns.append(url(r'^dataexport/market/$', data_export.export_view_json))
