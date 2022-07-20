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
def get_accounts_with_authorization(app_id: str, db_filter: str, value: str):
    """Gets all accounts with specified authorizations.

    It may be necessary to query all accounts with a certain
    authorization. This endpoint can query accounts and return that
    list of accounts.
    """
    accounts = Account.find_by_authorization(app_id, db_filter, value)

    return {
        'accounts': accounts
    }


@router.put('/update-authorization', tags=['Authorization'])
def update_authorization(body: UpdateAuthorizationRequestBody,
                         authorization: str = Header(default=None)):
    """Updates the authorization for a user for a given app.

    Apps can store data under each account regarding authorization.
    Apps can pass a dictionary to this endpoint which will be stored in
    the user's account. If no record exists for the app ID, a new
    record will be created. If a record already exists, it will be
    replaced with the new data.
    """
    account = Account.find_by_email(body.email)

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
    account = Account.find_by_email(email)

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
