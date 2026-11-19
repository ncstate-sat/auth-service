/**
 * The signed-in session: the auth/refresh token pair, kept in page memory
 * only. Reloading the page signs you out.
 */

import { request, setSessionBearerToken, errorMessage } from './api.js';
import { decodeJwt } from './jwt.js';

let currentSession = null;
const changeListeners = [];

/** listener(session | null) fires on sign-in, refresh, and sign-out. */
export function onSessionChange(listener) {
    changeListeners.push(listener);
}

export function getSession() {
    return currentSession;
}

export function isSignedIn() {
    return currentSession !== null;
}

export function startSession({ token, refreshToken }) {
    currentSession = {
        token,
        refreshToken,
        payload: decodeJwt(token)?.payload ?? {},
        refreshPayload: decodeJwt(refreshToken)?.payload ?? {},
    };
    setSessionBearerToken(token);
    notifySessionChange();
}

export function endSession() {
    currentSession = null;
    setSessionBearerToken(null);
    notifySessionChange();
}

/** Trades the session's refresh token for a new pair. Returns an error message, or null. */
export async function refreshSession() {
    if (!currentSession) {
        return 'Sign in before refreshing.';
    }
    const result = await request('POST', '/refresh-token', {
        body: { token: currentSession.refreshToken },
        auth: false,
    });
    if (!result.ok) {
        return errorMessage(result, 'Could not refresh the token.');
    }
    startSession({ token: result.body.token, refreshToken: result.body.refresh_token });
    return null;
}

function notifySessionChange() {
    for (const listener of changeListeners) {
        listener(currentSession);
    }
}
