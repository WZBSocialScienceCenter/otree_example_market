from collections import OrderedDict, Callable
from importlib import import_module

from django.db.models.fields import Field
from otree.views.admin import SessionData, pretty_name, pretty_round_name
from otree.export import sanitize_for_live_update, get_field_names_for_live_update, get_rows_for_live_update


# def get_rows_for_live_update(subsession):
#     models_module = import_module(subsession.__module__)
#     Player = models_module.Player
#     Group = models_module.Group
#     Subsession = models_module.Subsession
#
#     columns_for_models = {
#         Model.__name__.lower(): get_field_names_for_live_update(Model)
#         for Model in [Player, Group, Subsession]
#     }
#
#     # we had a strange result on one person's heroku instance
#     # where Meta.ordering on the Player was being ingnored
#     # when you use a filter. So we add one explicitly.
#     players = Player.objects.filter(
#         subsession_id=subsession.pk).select_related(
#         'group', 'subsession').order_by('pk')
#
#     model_order = ['player', 'group', 'subsession']
#
#     rows = []
#     for player in players:
#         row = []
#         for model_name in model_order:
#             if model_name == 'player':
#                 model_instance = player
#             else:
#                 model_instance = getattr(player, model_name)
#
#             for colname in columns_for_models[model_name]:
#
#                 attr = getattr(model_instance, colname, '')
#                 if isinstance(attr, Callable):
#                     if model_name == 'player' and colname == 'role' \
#                             and model_instance.group is None:
#                         attr = ''
#                     else:
#                         try:
#                             attr = attr()
#                         except:
#                             attr = "(error)"
#                 row.append(sanitize_for_live_update(attr))
#         rows.append(row)
#
#     return columns_for_models, rows


def get_field_names_for_custom_model(model):
    return [f.name for f in model._meta.fields]


def get_rows_for_live_update_from_custom_models(subsession, custom_model_names):
    models_module = import_module(subsession.__module__)

    custom_models = []   # classes

    for modelname in custom_model_names:
        try:
            custom_models.append(getattr(models_module, modelname))
        except AttributeError:
            raise ValueError('custom model `%s` not defined in models module')

    columns_for_models = {model.__name__.lower(): get_field_names_for_custom_model(model)
                          for model in custom_models}

    rows = []

    return columns_for_models, rows


class SessionDataExtension(SessionData):
    additional_models = []

    def get_context_data(self, **kwargs):
        def columns_for_any_modelname(modelname):
            cols = columns_for_custom_models.get(modelname, columns_for_models.get(modelname, []))
            if not cols:
                raise ValueError('No fields/columns for model `%s`' % model_name)
            return cols


        session = self.session

        rows = []

        round_headers = []
        model_headers = []
        field_names = []

        # field names for JSON response
        field_names_json = []

        for subsession in session.get_subsessions():
            # can't use subsession._meta.app_config.name, because it won't work
            # if the app is removed from SESSION_CONFIGS after the session is
            # created.
            columns_for_models, subsession_rows = get_rows_for_live_update(subsession)
            columns_for_custom_models, custom_models_rows = get_rows_for_live_update_from_custom_models(subsession, self.additional_models)

            if not rows:
                rows = subsession_rows
            else:
                for i in range(len(rows)):
                    rows[i].extend(subsession_rows[i])

            round_colspan = 0
            for model_name in ['player'] + list(columns_for_custom_models.keys()) + ['group', 'subsession']:
                colspan = len(columns_for_any_modelname(model_name))
                model_headers.append((model_name.title(), colspan))
                round_colspan += colspan

            round_name = pretty_round_name(subsession._meta.app_label, subsession.round_number)

            round_headers.append((round_name, round_colspan))

            this_round_fields = []
            this_round_fields_json = []
            for model_name in ['Player'] + self.additional_models + ['Group', 'Subsession']:
                column_names = columns_for_any_modelname(model_name.lower())
                this_model_fields = [pretty_name(n) for n in column_names]
                this_model_fields_json = [
                    '{}.{}.{}'.format(round_name, model_name, colname)
                    for colname in column_names
                ]
                this_round_fields.extend(this_model_fields)
                this_round_fields_json.extend(this_model_fields_json)

            field_names.extend(this_round_fields)
            field_names_json.extend(this_round_fields_json)

        # dictionary for json response
        # will be used only if json request  is done

        self.context_json = []
        for i, row in enumerate(rows, start=1):
            d_row = OrderedDict()
            # table always starts with participant 1
            d_row['participant_label'] = 'P{}'.format(i)
            for t, v in zip(field_names_json, row):
                d_row[t] = v
            self.context_json.append(d_row)

        context = super().get_context_data(**kwargs)
        context.update({
            'subsession_headers': round_headers,
            'model_headers': model_headers,
            'field_headers': field_names,
            'rows': rows})
        return context


    def get_template_names(self):
        return ['otree/admin/SessionData.html']

