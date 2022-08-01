"""Controller functions and routes for authorization CRUD."""

from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel
from models.Token import Token
from models.Account import Account

router = APIRouter()


class UpdateAuthorizationRequestBody(BaseModel):
    """Request body model."""
    authorization: dict
    app_id: str
    email: str


@router.get('/authorizations', tags=['Authorization'])
def get_accounts_with_authorization(response: Response,
                                    app_id: str,
                                    db_filter: str,
                                    value: str,
                                    authorization: str = Header(default=None)):
    """Gets all accounts with specified authorizations.

    It may be necessary to query all accounts with a certain
    authorization. This endpoint can query accounts and return that
    list of accounts.
    """

    # Get read permissions of the requesting account.
    requesting_account = Token.decode_token(authorization.split(' ')[1])
    requesting_account = Account.find_by_email(requesting_account['email'])
    read_permissions: dict = requesting_account.authorizations.get(
                                            app_id, {}).get('_read', {})

    # If requesting user has permission, return accounts data.
    if read_permissions.get(
        'superuser', False) is True or read_permissions.get(
            db_filter, False) is True:
        accounts = Account.find_by_authorization(app_id, db_filter, value)
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'error': """This account is not authorized to write to this
            user's authorization(s)."""
        }

    return {
        'accounts': accounts
    }


@router.put('/update-authorization', tags=['Authorization'])
def update_authorization(response: Response,
                         body: UpdateAuthorizationRequestBody,
                         authorization: str = Header(default=None)):
    """Updates the authorization for a user for a given app.

    Apps can store data under each account regarding authorization.
    Apps can pass a dictionary to this endpoint which will be stored in
    the user's account. If no record exists for the app ID, a new
    record will be created. If a record already exists, it will be
    replaced with the new data.
    """

    # Get write permissions of the requesting account.
    requesting_account = Token.decode_token(authorization.split(' ')[1])
    requesting_account = Account.find_by_email(requesting_account['email'])
    write_permissions: dict = requesting_account.authorizations.get(
                                            body.app_id, {}).get('_write', {})

    # If requesting user has permission, write new permission(s) to the database.
    if write_permissions.get('superuser', False) is True:
        account = Account.find_by_email(body.email)
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'error': """This account is not authorized to write to this
            user's authorization(s)."""
        }

    account.update_authorization(body.app_id, body.authorization)
    account.update()

    return {
        'authorizations': account.authorizations
    }


@router.delete('/delete-authorization', tags=['Authorization'])
def remove_authorization(response: Response,
                         app_id: str,
                         email: str,
                         authorization: str = Header(default=None)):
    """Removes a record of authorization from a user's account.

    Takes a value for app_id, then removes the entire record of
    authorization for that app in the user's account.
    """

    # Get write permissions of the requesting account.
    requesting_account = Token.decode_token(authorization.split(' ')[1])
    requesting_account = Account.find_by_email(requesting_account['email'])
    write_permissions: dict = requesting_account.authorizations.get(
                                            app_id, {}).get('_write', {})

    if write_permissions.get('superuser', False) is True:
        account = Account.find_by_email(email)
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'error': """This account is not authorized to delete
            this user's authorization(s)."""
        }

    try:
        account.remove_authorization(app_id)

    except RuntimeError as _:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'authorizations': account.authorizations,
            'message': 'This authorization already does not exsit.'
        }

    account.update()

    return {
        'authorizations': account.authorizations
    }
