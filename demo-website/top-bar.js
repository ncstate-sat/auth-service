/** The top bar's signed-in strip: identity, countdown, refresh, and sign out. */

import { announce } from './dom.js';
import { onSessionChange, refreshSession, endSession } from './session.js';
import { startCountdown, stopCountdown } from './session-countdown.js';
import { reportSessionStatus } from './session-page.js';

export function initTopBar() {
    document.getElementById('refresh-session').addEventListener('click', handleRefresh);
    document.getElementById('sign-out').addEventListener('click', handleSignOut);
    onSessionChange(renderTopBar);
}

function renderTopBar(session) {
    document.getElementById('top-bar-signed-in').hidden = !session;
    document.getElementById('top-bar-signed-out').hidden = Boolean(session);
    if (!session) {
        stopCountdown();
        return;
    }
    const email = session.payload.email ?? '(no email in token)';
    document.getElementById('top-bar-email').textContent = email;
    document.getElementById('top-bar-avatar').textContent = email.charAt(0).toUpperCase();
    startCountdown(session.payload.exp);
}

async function handleRefresh() {
    const failure = await refreshSession();
    const message = failure ?? 'Auth token refreshed. A new token pair was issued.';
    reportSessionStatus(message, failure ? 'error' : 'ok');
    announce(message);
}

function handleSignOut() {
    endSession();
    announce('Signed out.');
}
