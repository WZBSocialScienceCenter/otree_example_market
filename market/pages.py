from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import FruitOffer, Purchase
from django.forms import modelformset_factory


def get_offers_formset():
    return modelformset_factory(FruitOffer, fields=('kind', 'amount', 'price'), extra=1)


def get_purchases_formset(n_forms=0):
    return modelformset_factory(Purchase, fields=('amount', 'fruit'), extra=n_forms)


class CreateOffersPage(Page):
    def vars_for_template(self):
        OffersFormSet = get_offers_formset()

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

        OffersFormSet = get_offers_formset()

        offers_formset = OffersFormSet(self.form.data)
        offers_objs = []
        cost = 0    # total cost for the seller buying fruits that she or he can offer on the market
        for form_idx, form in enumerate(offers_formset.forms):
            if form.is_valid():
                offer = FruitOffer(**form.cleaned_data, seller=self.player)
                cost += offer.amount * FruitOffer.PURCHASE_PRICES[offer.kind]
                offers_objs.append(offer)
            else:   # invalid forms are not handled well so far -> we just ignore them
                print('player %d: invalid form #%d' % (self.player.id_in_group, form_idx))

        # store the offers in the DB
        FruitOffer.objects.bulk_create(offers_objs)

        # update seller's balance
        self.player.balance -= cost


class PurchasePage(Page):
    def vars_for_template(self):
        if self.player.role() == 'buyer':
            offers = FruitOffer.objects.select_related('seller__subsession', 'seller__participant').\
                filter(seller__subsession=self.player.subsession).\
                order_by('seller', 'kind')

            PurchasesFormSet = get_purchases_formset(len(offers))
            purchases_formset = PurchasesFormSet(initial=[{'amount': 0, 'fruit': offer}
                                                          for offer in offers])

            return {
                'purchases_formset': purchases_formset,
                'offers_with_forms': zip(offers, purchases_formset),
            }
        else:
            offers = FruitOffer.objects.filter(seller=self.player).order_by('kind')

            return {
                'sellers_offers': offers
            }

    def before_next_page(self):
        if self.player.role() == 'seller':
            return

        PurchasesFormSet = get_purchases_formset()

        purchases_formset = PurchasesFormSet(self.form.data)
        purchase_objs = []
        total_price = 0    # total cost for the customer
        for form_idx, form in enumerate(purchases_formset.forms):
            if form.is_valid() and form.cleaned_data['amount'] > 0:
                purchase = Purchase(**form.cleaned_data, buyer=self.player)
                purchase.fruit.amount -= purchase.amount        # decrease amount of available fruits
                prod = purchase.amount * purchase.fruit.price   # total price for this offer
                purchase.fruit.seller.balance += prod           # increase seller's balance
                total_price += prod                    # add to total price
                purchase_objs.append(purchase)

        # store the purchases in the DB
        Purchase.objects.bulk_create(purchase_objs)

        # update buyer's balance
        self.player.balance -= total_price


class Results(Page):
    def vars_for_template(self):
        if self.player.role() == 'buyer':
            transactions = Purchase.objects.select_related('buyer__subsession', 'buyer__participant',
                                                           'fruit__seller__participant'). \
                filter(buyer=self.player).\
                order_by('fruit__seller', 'fruit__kind')
        else:
            transactions = Purchase.objects.select_related('buyer__participant', 'fruit__seller'). \
                filter(fruit__seller=self.player).\
                order_by('buyer', 'fruit__kind')

        return {
            'transactions': transactions,
            'balance_change': sum([t.amount * t.fruit.price for t in transactions])
        }


page_sequence = [
    CreateOffersPage,
    WaitPage,
    PurchasePage,
    WaitPage,
    Results
]
