/**
 * The three-station login rail: Google credential → token exchange →
 * authorized payload. Completing station 2 starts the session and
 * unlocks the workbench.
 */

import { request, errorMessage } from './api.js';
import { prettyJson, syncScrollRegion } from './ui.js';
import { startSession } from './session.js';
import { createRail, renderJwt, clearJwt } from './rail.js';

const setStationStatus = createRail('', {
    1: 'Google credential',
    2: 'Token exchange',
    3: 'Authorized payload',
});

const JWT_PREFIXES = ['credential', 'token', 'refresh-token'];

/** Puts all three stations back to pending and clears their artifacts. */
export function resetHandshake() {
    for (const stationNumber of [1, 2, 3]) {
        setStationStatus(stationNumber, 'pending', null, { silent: true });
    }
    for (const prefix of JWT_PREFIXES) {
        clearJwt(prefix);
    }
    const payloadBlock = document.getElementById('raw-payload');
    payloadBlock.textContent = '';
    syncScrollRegion(payloadBlock, '');
}

/** Shown when Google Identity Services itself can't be loaded. */
export function reportSignInUnavailable(message) {
    setStationStatus(1, 'error', message);
}

/** The Google Identity Services callback — drives all three stations. */
export async function handleCredential(response) {
    resetHandshake();

    setStationStatus(1, 'active', null, { silent: true });
    renderJwt('credential', response.credential);
    setStationStatus(1, 'complete');

    setStationStatus(2, 'active');
    const signIn = await request('POST', '/google-sign-in', {
        body: { token: response.credential },
        auth: false,
    });
    if (!signIn.ok) {
        setStationStatus(2, 'error', errorMessage(signIn, 'The token exchange failed.'));
        return;
    }
    renderJwt('token', signIn.body.token);
    renderJwt('refresh-token', signIn.body.refresh_token);
    setStationStatus(2, 'complete');

    startSession(
        { token: signIn.body.token, refreshToken: signIn.body.refresh_token },
        'Signed in — the workbench is unlocked.',
    );

    setStationStatus(3, 'active');
    const login = await request('POST', '/login', {});
    if (!login.ok) {
        setStationStatus(3, 'error', errorMessage(login, 'The login call failed.'));
        return;
    }
    const payloadBlock = document.getElementById('raw-payload');
    payloadBlock.textContent = prettyJson(login.body);
    syncScrollRegion(payloadBlock, 'Response payload');
    setStationStatus(3, 'complete');
}
