"""
Export all data (including custom models such as FruitOffer and Purchase) as JSON.

This file contains several functions copy'n'pasted from oTrees's core code in order to retain compatibility with
future oTree versions.
"""

from collections import OrderedDict

from django.db.models import BinaryField
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from otree.models.participant import Participant
from otree.models.session import Session
from otree.models.subsession import BaseSubsession
from otree.models.group import BaseGroup
from otree.models.player import BasePlayer

from .models import Player


@login_required
def export_view_json(request):
    """
    Custom view function to export full results for this game as JSON file
    """

    # get the complete result data from the database
    qs_results = Player.objects.select_related('subsession', 'subsession__session', 'group', 'participant') \
        .prefetch_related('fruitoffer_set', 'purchase_set') \
        .all()

    session_fieldnames = []  # will be defined by get_field_names_for_csv
    subsess_fieldnames = []  # will be defined by get_field_names_for_csv
    group_fieldnames = []    # will be defined by get_field_names_for_csv
    player_fieldnames = []   # will be defined by get_field_names_for_csv
    fruitoffer_fieldnames = ['amount', 'price', 'kind']
    purchase_fieldnames = ['amount']

    # get all sessions, order them by label
    sessions = sorted(set([p.subsession.session for p in qs_results]), key=lambda x: x.label)

    # this will be a list that contains data of all sessions
    output = []

    # loop through all sessions
    for sess in sessions:
        session_fieldnames = session_fieldnames or get_field_names_for_csv(sess.__class__)
        sess_output = create_odict_from_object(sess, session_fieldnames)
        sess_output['subsessions'] = []

        # loop through all subsessions (i.e. rounds) ordered by round number
        subsessions = sorted(sess.get_subsessions(), key=lambda x: x.round_number)
        for subsess in subsessions:
            subsess_fieldnames = subsess_fieldnames or get_field_names_for_csv(subsess.__class__)
            subsess_output = create_odict_from_object(subsess, subsess_fieldnames)
            subsess_output['groups'] = []

            # loop through all groups ordered by ID
            groups = sorted(subsess.get_groups(), key=lambda x: x.id_in_subsession)
            for g in groups:
                group_fieldnames = group_fieldnames or get_field_names_for_csv(g.__class__)
                g_output = create_odict_from_object(g, group_fieldnames)
                g_output['players'] = []

                # loop through all players ordered by ID
                players = sorted(g.get_players(), key=lambda x: x.participant.id_in_session)
                for p in players:
                    player_fieldnames = player_fieldnames or get_field_names_for_csv(p.__class__)
                    p_output = create_odict_from_object(p, player_fieldnames)
                    p_output['role'] = p.role()

                    # add some additional player information
                    p_output['participant_id_in_session'] = p.participant.id_in_session

                    # add fruit offers if this is a "seller":
                    if p.role() == 'seller':
                        p_output['fruitoffers'] = []

                        # loop through all decisions ordered by ID
                        fruitoffers = p.fruitoffer_set.order_by('id')
                        for offer in fruitoffers:
                            offer_output = create_odict_from_object(offer, fruitoffer_fieldnames)
                            offer_output['fruitoffer_id'] = offer.id
                            p_output['fruitoffers'].append(offer_output)
                    else:  # add purchases if this is a "buyer"
                        assert p.role() == 'buyer'
                        p_output['purchases'] = []
                        purchases = p.purchase_set.order_by('id')
                        for purchase in purchases:
                            offer_output = create_odict_from_object(purchase, purchase_fieldnames)
                            offer_output['fruitoffer_id'] = purchase.fruit.id
                            p_output['purchases'].append(offer_output)

                    g_output['players'].append(p_output)

                subsess_output['groups'].append(g_output)

            sess_output['subsessions'].append(subsess_output)

        output.append(sess_output)

    return JsonResponse(output, safe=False)    # safe=False is necessary for exporting array structures


def create_odict_from_object(obj, fieldnames):
    """
    Small helper function to create an OrderedDict from an object <obj> using <fieldnames>
    as attributes.
    """
    data = OrderedDict()
    for f in fieldnames:
        data[f] = getattr(obj, f)

    return data


#################################
# code from oTree follows below #
# vvvvvvvvvvvvvvvvvvvvvvvvvvvvv #
#################################


def inspect_field_names(Model):
    # filter out BinaryField, because it's not useful for CSV export or
    # live results. could be very big, and causes problems with utf-8 export

    # I tried .get_fields() instead of .fields, but that method returns
    # fields that cause problems, like saying group has an attribute 'player'
    return [f.name for f in Model._meta.fields
            if not isinstance(f, BinaryField)]



def get_field_names_for_csv(Model):
    return _get_table_fields(Model, for_export=True)


def _get_table_fields(Model, for_export=False):

    if Model is Session:
        # only data export
        return [
            'code',
            'label',
            'experimenter_name',
            'mturk_HITId',
            'mturk_HITGroupId',
            'comment',
            'is_demo',
        ]

    if Model is Participant:
        if for_export:
            return [
                'id_in_session',
                'code',
                'label',
                '_is_bot',
                '_index_in_pages',
                '_max_page_index',
                '_current_app_name',
                '_round_number',
                '_current_page_name',
                'ip_address',
                'time_started',
                'visited',
                'mturk_worker_id',
                'mturk_assignment_id',
                # last so that it will be next to payoff_plus_participation_fee
                'payoff',
            ]
        else:
            return [
                '_id_in_session',
                'code',
                'label',
                '_current_page',
                '_current_app_name',
                '_round_number',
                '_current_page_name',
                'status',
                '_last_page_timestamp',
            ]

    if issubclass(Model, BasePlayer):
        subclass_fields = [
            f for f in inspect_field_names(Model)
            if f not in inspect_field_names(BasePlayer)
            and f not in ['id', 'group', 'subsession']
            ]

        if for_export:
            return ['id_in_group'] + subclass_fields + ['payoff']
        else:
            return ['id_in_group', 'role'] + subclass_fields + ['payoff']

    if issubclass(Model, BaseGroup):
        subclass_fields = [
            f for f in inspect_field_names(Model)
            if f not in inspect_field_names(BaseGroup)
            and f not in ['id', 'subsession']
            ]

        return ['id_in_subsession'] + subclass_fields

    if issubclass(Model, BaseSubsession):
        subclass_fields = [
            f for f in inspect_field_names(Model)
            if f not in inspect_field_names(BaseGroup)
            and f != 'id'
            ]

        return ['round_number'] + subclass_fields
