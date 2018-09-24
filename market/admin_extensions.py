from collections import OrderedDict, defaultdict
from importlib import import_module
from pprint import pprint

from otree.views.admin import SessionData, pretty_name, pretty_round_name
from otree.export import sanitize_for_live_update, get_rows_for_live_update


class SessionDataExtension(SessionData):
    custom_models = []   # model names as strings (case-sensitive!), *not* model classes

    @classmethod
    def get_field_names_for_custom_model(cls, model):
        return [f.name for f in model._meta.fields]

    def custom_rows_queryset(self, models_module, **kwargs):
        base_model = getattr(models_module, 'Player')
        prefetch_related_args = [m.lower() + '_set' for m in self.custom_models]

        return base_model.objects\
            .filter(subsession_id=kwargs['subsession'].pk)\
            .prefetch_related(*prefetch_related_args)

    def custom_rows_builder(self, qs, columns_for_custom_models):
        rows = defaultdict(lambda: defaultdict(list))

        for base_instance in qs:
            for model_name in self.custom_models:
                model_name_lwr = model_name.lower()
                row = []
                model_results_set = getattr(base_instance, model_name_lwr + '_set').all()
                for res in model_results_set:
                    for colname in columns_for_custom_models[model_name_lwr]:
                        attr = getattr(res, colname, '')
                        row.append(sanitize_for_live_update(attr))
                rows[str(base_instance.id)][model_name].append(row)

        return rows

    def custom_columns_builder(self, models_module):
        custom_model_classes = []

        for modelname in self.custom_models:
            try:
                custom_model_classes.append(getattr(models_module, modelname))
            except AttributeError:
                raise ValueError('custom model `%s` not defined in models module')

        columns_for_models = {model.__name__.lower(): self.get_field_names_for_custom_model(model)
                              for model in custom_model_classes}

        return columns_for_models

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
            models_module = import_module(subsession.__module__)
            columns_for_custom_models = self.custom_columns_builder(models_module)
            custom_models_qs = self.custom_rows_queryset(models_module, subsession=subsession)
            custom_rows = self.custom_rows_builder(custom_models_qs, columns_for_custom_models)
            pprint(columns_for_custom_models)
            pprint(custom_rows)

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
            for model_name in ['Player'] + self.custom_models + ['Group', 'Subsession']:
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

