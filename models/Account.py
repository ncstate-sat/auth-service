import util.db as db


class Account:
    id = None
    email = None
    campus_id = None
    authorizations = {}

    def __init__(self, config):
        if 'id' in config:
            self.id = config['id']
        if 'email' in config:
            self.email = config['email']
        if 'campus_id' in config:
            self.campus_id = config['campus_id']
        if 'authorizations' in config:
            self.authorizations = config['authorizations']

    def update(self):
        return db.update_account_by_id(self.id, self.__dict__)

    def delete(self):
        return db.delete_account_by_id(self.id)

    def get_authorization(self, service_name):
        return self.authorizations[service_name]

    def update_authorization(self, service_name, auth_info):
        self.authorizations[service_name] = auth_info
        return

    def remove_authorization(self, service_name):
        return self.authorizations.pop(service_name)

    @staticmethod
    def find_by_id(account_id):
        db_account = db.get_account_by_id(account_id)
        return Account(config=db_account)

    @staticmethod
    def find_by_email(email):
        db_account = db.get_account_by_email(email)
        return Account(config=db_account)

    @staticmethod
    def find_by_campus_id(campus_id):
        db_account = db.get_account_by_campus_id(campus_id)
        return Account(config=db_account)

    @staticmethod
    def create_account(email, campus_id, authorizations):
        account_data = db.create_account(email, campus_id, authorizations)
        return Account(config=account_data)
