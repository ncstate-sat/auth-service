/** The #session page: the start guide when signed out, your tokens when signed in. */

import { el, prettyJson, setCodeBlock, setInlineStatus } from './dom.js';
import { copyWithConfirmation } from './clipboard.js';
import { onSessionChange, getSession } from './session.js';

export function initSessionPage() {
    document.getElementById('copy-auth-token').addEventListener('click', (event) => {
        copyWithConfirmation(event.currentTarget, getSession()?.token ?? '');
    });
    document.getElementById('copy-refresh-token').addEventListener('click', (event) => {
        copyWithConfirmation(event.currentTarget, getSession()?.refreshToken ?? '');
    });
    onSessionChange(renderSessionDetails);
}

/** The heading to focus when the page is shown, which depends on whether you're signed in. */
export function showSessionPage() {
    const signedIn = getSession() !== null;
    document.getElementById('view-start').hidden = signedIn;
    document.getElementById('view-session').hidden = !signedIn;
    return document.getElementById(signedIn ? 'session-title' : 'start-title');
}

export function hideSessionPage() {
    document.getElementById('view-start').hidden = true;
    document.getElementById('view-session').hidden = true;
}

export function reportSessionStatus(message, tone) {
    setInlineStatus('session-status', message, tone);
}

function renderSessionDetails(session) {
    if (!session) {
        reportSessionStatus('');
        return;
    }
    const { payload } = session;
    document.getElementById('session-email').textContent = payload.email ?? '(no email in token)';
    document.getElementById('session-account-type').textContent = payload.account_type ?? 'user';
    document.getElementById('session-roles').replaceChildren(...buildRoleChips(payload.roles ?? []));
    setCodeBlock(document.getElementById('auth-token-payload'), prettyJson(payload));
    setCodeBlock(document.getElementById('refresh-token-payload'), prettyJson(session.refreshPayload));
}

function buildRoleChips(roles) {
    if (!roles.length) {
        return [el('span', { className: 'hint', text: 'none yet' })];
    }
    return roles.map((role) => el('span', { className: 'chip', text: role }));
}
