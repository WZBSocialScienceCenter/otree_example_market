from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Constants, FruitOffer
from django.forms import modelformset_factory


OffersFormSet = modelformset_factory(FruitOffer, fields=('kind', 'is_organic', 'amount', 'price'), extra=1)


class CreateOffersPage(Page):
    def vars_for_template(self):
        return {
            'offers_formset': OffersFormSet,
        }


class PurchasePage(Page):
    pass


class Results(Page):
    pass


page_sequence = [
    CreateOffersPage,
    WaitPage,
    PurchasePage,
    WaitPage,
    Results
]
