/**
 * The three-station login rail: Google credential → token exchange →
 * authorized payload. Completing station 2 starts the session and
 * unlocks the workbench.
 */

import { request, errorMessage } from './api.js';
import { decodeJwt, prettyJson, announce } from './ui.js';
import { startSession } from './session.js';

const STATUS_LABELS = {
    pending: 'Pending',
    active: 'In progress',
    complete: 'Complete',
    error: 'Error',
};

const STATION_TITLES = {
    1: 'Google credential',
    2: 'Token exchange',
    3: 'Authorized payload',
};

const JWT_PREFIXES = ['credential', 'token', 'refresh-token'];

function setStationStatus(stationNumber, status, errorText, { silent = false } = {}) {
    const station = document.getElementById(`station-${stationNumber}`);
    station.classList.remove('station--pending', 'station--active', 'station--complete', 'station--error');
    station.classList.add(`station--${status}`);

    const badge = station.querySelector(`[data-status-for="${stationNumber}"]`);
    badge.classList.remove('status-badge--pending', 'status-badge--active', 'status-badge--complete', 'status-badge--error');
    badge.classList.add(`status-badge--${status}`);
    badge.textContent = STATUS_LABELS[status];

    const errorEl = document.getElementById(`station-error-${stationNumber}`);
    if (status === 'error' && errorText) {
        errorEl.textContent = errorText;
        errorEl.hidden = false;
    } else {
        errorEl.hidden = true;
    }

    if (!silent) {
        announce(`Step ${stationNumber}, ${STATION_TITLES[stationNumber]}: ${STATUS_LABELS[status]}.`);
    }
}

function renderJwt(prefix, token) {
    document.getElementById(`raw-${prefix}`).textContent = token;

    const decoded = decodeJwt(token);
    const details = document.getElementById(`details-${prefix}`);
    if (decoded) {
        document.getElementById(`decoded-${prefix}-header`).textContent = prettyJson(decoded.header);
        document.getElementById(`decoded-${prefix}-payload`).textContent = prettyJson(decoded.payload);
        details.hidden = false;
    } else {
        details.hidden = true;
    }
}

/** Puts all three stations back to pending and clears their artifacts. */
export function resetHandshake() {
    for (const stationNumber of [1, 2, 3]) {
        setStationStatus(stationNumber, 'pending', null, { silent: true });
    }
    for (const prefix of JWT_PREFIXES) {
        document.getElementById(`raw-${prefix}`).textContent = '';
        const details = document.getElementById(`details-${prefix}`);
        details.hidden = true;
        details.open = false;
    }
    document.getElementById('raw-payload').textContent = '';
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
    document.getElementById('raw-payload').textContent = prettyJson(login.body);
    setStationStatus(3, 'complete');
}
