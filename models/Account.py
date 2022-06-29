class Account:
    email = None
    campus_id = None
    authorizations = {}

    def __init__(self):
        pass

    def get_authorization(self, service_name):
        return self.authorizations[service_name]

    def update_authorization(self, service_name, auth_info):
        self.authorizations[service_name] = auth_info
        return

    def remove_authorization(self, service_name):
        self.authorizations.pop(service_name)