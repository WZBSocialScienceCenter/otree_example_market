from collections import OrderedDict, defaultdict
from importlib import import_module
from pprint import pprint

from otree.views.admin import SessionData, AdminSessionPageMixin, pretty_name, pretty_round_name
from otree.export import sanitize_for_live_update, get_rows_for_live_update
from otree.db.models import Model


class SessionDataExtension(SessionData):
    @staticmethod
    def get_field_names_for_custom_model(model):
        return [f.name for f in model._meta.fields]

    @staticmethod
    def get_custom_models_conf(models_module):
        custom_models_conf = {}
        for attr in dir(models_module):
            val = getattr(models_module, attr)
            try:
                if issubclass(val, Model):
                    metaclass = getattr(val, 'CustomModelConf', None)
                    if metaclass and hasattr(metaclass, 'data_view'):
                        custom_models_conf[attr] = {
                            'class': val,
                            'data_view': getattr(metaclass, 'data_view')
                        }
            except TypeError:
                pass

        return custom_models_conf

    @staticmethod
    def custom_rows_queryset(models_module, custom_models_names,  **kwargs):
        base_class = 'Player'
        base_key = 'id_in_group'
        base_model = getattr(models_module, base_class)
        prefetch_related_args = [m.lower() + '_set' for m in custom_models_names]

        return (base_model.objects\
            .filter(subsession_id=kwargs['subsession'].pk)\
            .prefetch_related(*prefetch_related_args),
            base_class,
            base_key)

    @staticmethod
    def custom_rows_builder(qs, columns_for_custom_models, custom_models_baseclass, custom_models_basekey):
        rows = defaultdict(lambda: defaultdict(list))

        for base_instance in qs:
            key = str(getattr(base_instance, custom_models_basekey))

            for model_name_lwr, colnames in columns_for_custom_models.items():
                model_results_set = getattr(base_instance, model_name_lwr + '_set').all()

                for res in model_results_set:
                    row = []
                    for colname in colnames:
                        attr = getattr(res, colname, '')
                        row.append(sanitize_for_live_update(attr))

                    rows[key][model_name_lwr].append(row)

        return rows

    def custom_columns_builder(self, custom_model_classes):
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
            models_module = import_module(subsession.__module__)
            custom_models_conf = self.get_custom_models_conf(models_module)
            custom_models_names = list(custom_models_conf.keys())
            custom_models_names_lwr = [n.lower() for n in custom_models_names]
            custom_models_classes = [conf['class'] for conf in custom_models_conf.values()]

            # can't use subsession._meta.app_config.name, because it won't work
            # if the app is removed from SESSION_CONFIGS after the session is
            # created.
            columns_for_models, subsession_rows = get_rows_for_live_update(subsession)

            columns_for_custom_models = self.custom_columns_builder(custom_models_classes)
            custom_models_qs, custom_models_baseclass, custom_models_basekey = \
                self.custom_rows_queryset(models_module, custom_models_names, subsession=subsession)
            custom_rows = self.custom_rows_builder(custom_models_qs, columns_for_custom_models,
                                                   custom_models_baseclass, custom_models_basekey)
            pprint(subsession_rows)
            pprint(columns_for_custom_models)
            pprint(custom_rows)

            combined_rows = []
            otree_modelnames = ['Player', 'Group', 'Subsession']
            otree_modelnames_lwr = [n.lower() for n in otree_modelnames]
            for row in subsession_rows:
                # find row key
                row_key = None

                i = 0
                for ot_model_name in otree_modelnames:
                    model_fields = columns_for_any_modelname(ot_model_name.lower())
                    n_fields = len(model_fields)

                    if ot_model_name == custom_models_baseclass:
                        try:
                            key_idx = model_fields.index(custom_models_basekey)
                            row_key = row[i + key_idx]
                        except ValueError:   # custom_models_basekey not in model_fields
                            pass

                    i += n_fields

                if row_key is None:
                    raise ValueError('no row key found (base class: `%s`, key name: `%s`)'
                                     % (custom_models_baseclass, custom_models_basekey))

                combrow = []  # combined row
                n_fields_from_otree_models = 0
                for model_name in ['player'] + custom_models_names_lwr + ['group', 'subsession']:
                    n_fields = len(columns_for_any_modelname(model_name))

                    if model_name in otree_modelnames_lwr:
                        field_idx_start = n_fields_from_otree_models
                        field_idx_end = n_fields_from_otree_models + n_fields
                        combrow.extend(row[field_idx_start:field_idx_end])
                        n_fields_from_otree_models += n_fields
                    else:
                        custom_vals = custom_rows[row_key][model_name]
                        if custom_vals:
                            assert all(n == n_fields for n in map(len, custom_vals))
                            for col_values in zip(*custom_rows[row_key][model_name]):
                                combrow.append(','.join(col_values))
                        else:
                            combrow.extend([''] * n_fields)

                combined_rows.append(combrow)

            pprint(combined_rows)
            n_cols_otree_models = sum(map(len, columns_for_models.values()))
            n_cols_custom_models = sum(map(len, columns_for_custom_models.values()))
            assert all(n == n_cols_otree_models + n_cols_custom_models for n in map(len, combined_rows))

            if not rows:
                rows = combined_rows
            else:
                for i in range(len(rows)):
                    rows[i].extend(combined_rows[i])

            round_colspan = 0
            for model_name in ['player'] + custom_models_names_lwr + ['group', 'subsession']:
                colspan = len(columns_for_any_modelname(model_name))
                model_headers.append((model_name.title(), colspan))
                round_colspan += colspan

            round_name = pretty_round_name(subsession._meta.app_label, subsession.round_number)

            round_headers.append((round_name, round_colspan))

            this_round_fields = []
            this_round_fields_json = []
            for model_name in ['Player'] + custom_models_names + ['Group', 'Subsession']:
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

        context = super(SessionData, self).get_context_data(**kwargs)   # calls `get_context_data()` from
                                                                        # AdminSessionPageMixin
        context.update({
            'subsession_headers': round_headers,
            'model_headers': model_headers,
            'field_headers': field_names,
            'rows': rows})
        return context

    def get_template_names(self):
        return ['otree/admin/SessionData.html']

