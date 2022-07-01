from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel
from models.Token import Token
from models.Account import Account

router = APIRouter()


class UpdateAuthorizationRequestBody(BaseModel):
    authorization: dict
    app_id: str


@router.put('/update-authorization', tags=['Authorization'])
def update_authorization(body: UpdateAuthorizationRequestBody, authorization: str = Header(default=None)):
    """Updates the authorization for a user for a given app.

    Apps can store data under each account regarding authorization. Apps can pass a dictionary to this endpoint which will be stored in the user's account. If no record exists for the app ID, a new record will be created. If a record already exists, it will be replaced with the new data.
    """
    token = authorization.split(' ')[1]
    payload = Token.decode_token(token)
    account_email = payload['email']

    account = Account.find_by_email(account_email)

    account.authorizations[body.app_id] = body.authorization
    account.update()

    return {
        'authorizations': account.authorizations
    }


@router.delete('/delete-authorization/{app_id}', tags=['Authorization'])
def remove_authorization(response: Response, app_id: str, authorization: str = Header(default=None)):
    """Removes a record of authorization from a user's account.

    Takes a value for app_id, then removes the entire record of authorization for that app in the user's account.
    """
    token = authorization.split(' ')[1]
    payload = Token.decode_token(token)
    account_email = payload['email']

    account = Account.find_by_email(account_email)

    if app_id in account.authorizations:
        account.authorizations.pop(app_id)
        account.update()
    else:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {
            'authorizations': account.authorizations,
            'message': 'This authorization already does not exsit.'
        }

    return {
        'authorizations': account.authorizations
    }
