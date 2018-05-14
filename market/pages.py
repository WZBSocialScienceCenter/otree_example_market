import json

from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Constants, FruitOffer
from django.forms import modelformset_factory


OffersFormSet = modelformset_factory(FruitOffer, fields=('kind', 'amount', 'price'), extra=1)


class CreateOffersPage(Page):
    def vars_for_template(self):
        if self.player.role() == 'seller':
            player_offers_qs = FruitOffer.objects.filter(seller=self.player)
            return {
                'purchase_prices': FruitOffer.PURCHASE_PRICES,
                'offers_formset': OffersFormSet(queryset=player_offers_qs),
            }
        else:
            return {}

    def before_next_page(self):
        if self.player.role() == 'buyer':
            return

        offers_formset = OffersFormSet(self.form.data)

        for form_idx, form in enumerate(offers_formset.forms):
            if form.is_valid():
                offer = FruitOffer.objects.create(**form.cleaned_data, seller=self.player)
                offer.save()
            else:   # TODO: invalid forms are not handled well so far
                print('player %d: invalid form #%d' % (self.player.id_in_group, form_idx))


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
