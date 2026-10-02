/**
 * The service account rail: pasted Google credential → token exchange →
 * a call made as the service account. The service account's token is
 * kept here and sent per-request, so it never replaces the signed-in
 * user's session.
 */

import { API_BASE, request, errorMessage } from './api.js';
import { prettyJson, announce, syncScrollRegion } from './ui.js';
import { createRail, renderJwt, clearJwt } from './rail.js';

const setStationStatus = createRail('sa-', {
    1: 'Google credential',
    2: 'Token exchange',
    3: 'Call as the service account',
}, 'Service account step');

const JWT_PREFIXES = ['sa-credential', 'sa-token'];

export function initServiceHandshake(defaultAudience) {
    const keyPathInput = document.getElementById('sa-mint-key-path');
    const audienceInput = document.getElementById('sa-mint-audience');
    audienceInput.value = defaultAudience ?? '';

    const snippet = document.getElementById('sa-python-snippet');
    snippet.closest('details').addEventListener('toggle', () => syncScrollRegion(snippet, 'Python example'));

    keyPathInput.addEventListener('input', () => {
        rejectPastedKey(keyPathInput);
        renderSnippets();
    });
    audienceInput.addEventListener('input', renderSnippets);
    renderSnippets();

    document.getElementById('sa-exchange-form').addEventListener('submit', handleExchange);
    document.getElementById('sa-reset').addEventListener('click', () => {
        document.getElementById('sa-credential-input').value = '';
        resetServiceHandshake();
        document.getElementById('sa-credential-input').focus();
    });
}

function renderSnippets() {
    const keyPath = document.getElementById('sa-mint-key-path').value.trim() || 'path/to/key.json';
    const audience = document.getElementById('sa-mint-audience').value.trim() || 'AUDIENCE';

    document.getElementById('sa-mint-command').textContent = [
        `python -m util.service_account_credential ${shellQuote(keyPath)} \\`,
        `  --audience ${shellQuote(audience)}`,
    ].join('\n');

    document.getElementById('sa-python-snippet').textContent = `import requests
import google.auth.transport.requests
from google.oauth2 import id_token

AUTH_SERVICE = '${API_BASE}'
AUDIENCE = '${audience}'


def get_auth_token():
    # On Google Cloud, this asks the metadata server for an ID token for the
    # attached service account. Elsewhere, it uses the key file named by
    # GOOGLE_APPLICATION_CREDENTIALS.
    google_token = id_token.fetch_id_token(google.auth.transport.requests.Request(), AUDIENCE)

    response = requests.post(f'{AUTH_SERVICE}/service-account/google-sign-in',
                             json={'token': google_token})
    response.raise_for_status()
    return response.json()['token']


# Call another service with the auth token as a bearer token.
requests.get('https://reports.university.edu/api/summary',
             headers={'Authorization': f'Bearer {get_auth_token()}'})`;
}

/* The field takes a path to the key file. If the key itself is pasted
   in, clear it right away, so the private key never lands in the
   command (and from there in a shell history). */
function rejectPastedKey(input) {
    const value = input.value;
    const looksLikeKey = value.trimStart().startsWith('{') || value.includes('PRIVATE KEY');
    const error = document.getElementById('sa-mint-key-error');

    if (looksLikeKey) {
        input.value = '';
        input.setAttribute('aria-invalid', 'true');
        error.textContent = 'That looks like the key itself, so it was cleared. '
            + 'Enter the path to the key file instead, and avoid pasting keys into web pages.';
        error.hidden = false;
        announce(error.textContent);
    } else if (value) {
        input.removeAttribute('aria-invalid');
        error.textContent = '';
        error.hidden = true;
    }
}

/** Quotes a value for a POSIX shell, unless it's made only of safe characters. */
function shellQuote(value) {
    return /^[\w@%+=:,./-]+$/.test(value) ? value : `'${value.replace(/'/g, "'\\''")}'`;
}

/** Puts all three stations back to pending and clears their artifacts. */
export function resetServiceHandshake() {
    for (const stationNumber of [1, 2, 3]) {
        setStationStatus(stationNumber, 'pending', null, { silent: true });
    }
    for (const prefix of JWT_PREFIXES) {
        clearJwt(prefix);
    }
    const payloadBlock = document.getElementById('raw-sa-payload');
    payloadBlock.textContent = '';
    syncScrollRegion(payloadBlock, '');
}

async function handleExchange(event) {
    event.preventDefault();
    const credential = document.getElementById('sa-credential-input').value.trim();

    resetServiceHandshake();

    setStationStatus(1, 'active', null, { silent: true });
    if (!renderJwt('sa-credential', credential)) {
        setStationStatus(1, 'error',
            "That doesn't look like a JWT. Paste the whole token that the command printed.");
        return;
    }
    setStationStatus(1, 'complete');

    setStationStatus(2, 'active');
    const signIn = await request('POST', '/service-account/google-sign-in', {
        body: { token: credential },
        auth: false,
    });
    if (!signIn.ok) {
        setStationStatus(2, 'error', errorMessage(signIn, 'The token exchange failed.'));
        return;
    }
    renderJwt('sa-token', signIn.body.token);
    setStationStatus(2, 'complete');

    setStationStatus(3, 'active');
    const login = await request('POST', '/login', { asServiceAccount: signIn.body.token });
    if (!login.ok) {
        setStationStatus(3, 'error', errorMessage(login, 'The login call failed.'));
        return;
    }
    const payloadBlock = document.getElementById('raw-sa-payload');
    payloadBlock.textContent = prettyJson(login.body);
    syncScrollRegion(payloadBlock, 'Service account response payload');
    setStationStatus(3, 'complete');
}
