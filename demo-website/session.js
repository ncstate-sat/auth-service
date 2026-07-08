/**
 * Session state: the auth/refresh token pair, the countdown to expiry,
 * and the signed-in strip in the masthead. Tokens are kept in page
 * memory only — reloading the page signs you out.
 */

import { request, setBearerToken, errorMessage } from './api.js';
import { decodeJwt, el, prettyJson, announce, setStatus } from './ui.js';

let state = null; // { token, refreshToken, payload }
let countdownTimer = null;
let announcedThresholds = new Set();
const changeListeners = [];

/** listener(isSignedIn, email) — fires on sign-in, refresh, and sign-out. */
export function onSessionChange(listener) {
    changeListeners.push(listener);
}

function notifyChange() {
    for (const listener of changeListeners) {
        listener(state !== null, state?.payload?.email ?? null);
    }
}

export function getSessionEmail() {
    return state?.payload?.email ?? null;
}

export function initSession() {
    document.getElementById('session-refresh').addEventListener('click', refreshSession);
    document.getElementById('session-sign-out').addEventListener('click', () => {
        endSession();
        announce('Signed out.');
    });
}

export function startSession({ token, refreshToken }, statusMessage = '') {
    state = {
        token,
        refreshToken,
        payload: decodeJwt(token)?.payload ?? {},
    };
    setBearerToken(token);
    renderSignedIn();
    startCountdown();
    setStatus('session-status', statusMessage, 'ok');
    notifyChange();
}

export function endSession() {
    state = null;
    setBearerToken(null);
    stopCountdown();
    document.getElementById('session-signed-in').hidden = true;
    document.getElementById('session-signed-out').hidden = false;
    setStatus('session-status', '');
    notifyChange();
}

function renderSignedIn() {
    document.getElementById('session-signed-out').hidden = true;
    document.getElementById('session-signed-in').hidden = false;

    document.getElementById('session-email').textContent = state.payload.email ?? '(no email in token)';
    document.getElementById('session-roles').replaceChildren(
        ...(state.payload.roles ?? []).map((role) => el('span', { className: 'chip', text: role })),
    );

    document.getElementById('session-token-raw').textContent = state.token;
    document.getElementById('session-token-payload').textContent =
        prettyJson(decodeJwt(state.token)?.payload ?? null);
    document.getElementById('session-refresh-raw').textContent = state.refreshToken;
    document.getElementById('session-refresh-payload').textContent =
        prettyJson(decodeJwt(state.refreshToken)?.payload ?? null);
}

async function refreshSession() {
    if (!state) {
        return;
    }
    const result = await request('POST', '/refresh-token', {
        body: { token: state.refreshToken },
        auth: false,
    });
    if (!result.ok) {
        setStatus('session-status', errorMessage(result, 'Could not refresh the token.'), 'error');
        return;
    }
    startSession(
        { token: result.body.token, refreshToken: result.body.refresh_token },
        'Token refreshed — new pair issued.',
    );
    announce('Auth token refreshed.');
}

/* ── Expiry countdown ──────────────────────────────────────────────
   The value updates every second but is NOT in a live region; screen
   readers only hear the 5-minute, 1-minute, and expired thresholds. */

function startCountdown() {
    stopCountdown();
    announcedThresholds = new Set();
    tick();
    countdownTimer = setInterval(tick, 1000);
}

function stopCountdown() {
    if (countdownTimer !== null) {
        clearInterval(countdownTimer);
        countdownTimer = null;
    }
}

function tick() {
    const label = document.getElementById('session-countdown-label');
    const value = document.getElementById('session-countdown-value');
    const exp = state?.payload?.exp;

    if (!exp) {
        label.textContent = 'Auth token expiry';
        value.textContent = 'not present in token';
        return;
    }

    const secondsLeft = Math.floor(exp - Date.now() / 1000);

    if (secondsLeft <= 0) {
        label.textContent = 'Auth token';
        value.textContent = 'expired — refresh to continue';
        value.classList.add('session__countdown-value--warning');
        announceThreshold(0, 'Auth token expired. Use the refresh button to get a new one.');
        stopCountdown();
        return;
    }

    label.textContent = 'Auth token expires in';
    const minutes = Math.floor(secondsLeft / 60);
    const seconds = secondsLeft % 60;
    value.textContent = `${minutes}:${String(seconds).padStart(2, '0')}`;
    value.classList.toggle('session__countdown-value--warning', secondsLeft <= 60);

    if (secondsLeft <= 60) {
        announceThreshold(60, 'Auth token expires in under a minute.');
    } else if (secondsLeft <= 300) {
        announceThreshold(300, 'Auth token expires in under five minutes.');
    }
}

function announceThreshold(threshold, message) {
    if (!announcedThresholds.has(threshold)) {
        announcedThresholds.add(threshold);
        announce(message);
    }
}
