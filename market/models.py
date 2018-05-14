import random

from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)

from otree.db.models import ForeignKey, Model

author = 'Markus Konrad'

doc = """
Example experiment: selling/buying products on a market.
Implemented with custom data models.

Many individuals (1 ... N-1) are selling items with two attributes (e.g. colour and price). Each chooses a colour
and a price. Then individual N needs to choose which items to buy.  
"""


class Constants(BaseConstants):
    name_in_url = 'market'
    players_per_group = None
    num_rounds = 1


class Subsession(BaseSubsession):
    def creating_session(self):   # oTree 2 method name (used to be before_session_starts)
        if self.round_number == 1:
            for p in self.get_players():
                p.balance = c(random.triangular(1, 20, 10))


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    balance = models.CurrencyField()

    def role(self):
        if self.id_in_group == 1:
            return 'buyer'
        else:
            return 'seller'


class FruitOffer(Model):
    KINDS = (
        ('apple', 'Apple'),
        ('orange', 'Orange'),
        ('banana', 'Banana'),
    )

    amount = models.IntegerField(label='Amount', min=0, initial=0)           # number of fruits available
    price = models.CurrencyField(label='Price per fruit', min=0, initial=0)
    kind = models.StringField(choices=KINDS)
    is_organic = models.BooleanField()   # if True: organic fruit, else conventional

    seller = ForeignKey(Player)    # creates many-to-one relation -> this fruit is sold by a certain player, a player
                                   # can sell many fruits


class Purchases(Model):
    """
    This also links each purchase via `FruitOffer` to a seller
    """
    amount = models.IntegerField(min=1)    # fruits taken
    # price = models.CurrencyField(min=0)   optional: allow bargaining

    fruit = ForeignKey(FruitOffer)     # creates many-to-one relation -> this purchase relates to a certain fruit offer
                                       # many purchases can be made for this offer (as long as there's more than 0
                                       # fruits left)
    buyer = ForeignKey(Player)         # creates many-to-one relation -> this fruit is bought by a certain player
                                       # *in a certain round*. a player can buy many fruits.

