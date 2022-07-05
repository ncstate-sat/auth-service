import util.db as db


class Account:
    email = None
    campus_id = None
    authorizations = {}

    def __init__(self, config):
        if 'email' in config:
            self.email = config['email']
        if 'campus_id' in config:
            self.campus_id = config['campus_id']
        if 'authorizations' in config:
            self.authorizations = config['authorizations']

    def update(self):
        return db.update_account(self.__dict__)

    def delete(self):
        return db.delete_account(self.id)

    def get_authorization(self, service_name):
        return self.authorizations[service_name]

    def update_authorization(self, service_name, auth_info):
        self.authorizations[service_name] = auth_info
        return

    def remove_authorization(self, service_name):
        return self.authorizations.pop(service_name)

    @staticmethod
    def find_by_email(email):
        db_account = db.get_account_by_email(email)
        if db_account is None:
            new_account = Account.create_account(email, None)
            return new_account
        else:
            return Account(config=db_account)

    @staticmethod
    def create_account(email, campus_id, authorizations={}):
        account_data = {'email': email, 'campus_id': campus_id,
                        'authorizations': authorizations}
        db.create_account(account_data)
        return Account(config=account_data)
