from otree.views.admin import SessionData


class SessionDataExtension(SessionData):
    def get_template_names(self):
        return ['otree/admin/SessionData.html']

