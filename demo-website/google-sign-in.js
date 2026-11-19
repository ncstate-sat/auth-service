/**
 * Google Identity Services sign-in: renders Google's button into every
 * [data-google-button] slot and runs the credential → token exchange flow.
 */

import { request, errorMessage } from './api.js';
import { announce, el } from './dom.js';
import { startSession } from './session.js';
import { saveResponse } from './response-store.js';

export const GOOGLE_SIGN_IN_ENDPOINT_ID = 'google-sign-in';

const GSI_RETRY_MS = 300;
const GSI_TIMEOUT_MS = 6000;

const FLOW_STEPS = [
    { title: 'Google credential', where: 'accounts.google.com' },
    { title: 'Token exchange', where: 'POST /google-sign-in' },
    { title: 'Auth + refresh tokens', where: 'kept in page memory' },
];

let flowStatuses = FLOW_STEPS.map(() => 'pending');
let flowError = null;
const flowListeners = [];

/** listener({ steps, error }) fires whenever a step changes status. */
export function onSignInFlowChange(listener) {
    flowListeners.push(listener);
}

export function getSignInFlow() {
    return {
        steps: FLOW_STEPS.map((step, index) => ({ ...step, status: flowStatuses[index] })),
        error: flowError,
    };
}

export function resetSignInFlow() {
    flowStatuses = FLOW_STEPS.map(() => 'pending');
    flowError = null;
    notifyFlowChange();
}

export function initGoogleSignIn(googleClientId) {
    waitForGoogleIdentityServices(0, () => {
        google.accounts.id.initialize({ client_id: googleClientId, callback: handleCredential });
        renderGoogleButtons();
    });
}

function waitForGoogleIdentityServices(waitedMs, onReady) {
    if (typeof google !== 'undefined' && google.accounts) {
        onReady();
        return;
    }
    if (waitedMs >= GSI_TIMEOUT_MS) {
        reportGoogleUnavailable();
        return;
    }
    setTimeout(() => waitForGoogleIdentityServices(waitedMs + GSI_RETRY_MS, onReady), GSI_RETRY_MS);
}

function renderGoogleButtons() {
    for (const slot of document.querySelectorAll('[data-google-button]')) {
        google.accounts.id.renderButton(slot, {
            theme: 'outline',
            size: slot.dataset.googleButton,
            text: 'signin_with',
            width: slot.dataset.googleButton === 'large' ? 240 : 200,
        });
    }
}

function reportGoogleUnavailable() {
    const message = 'Google sign-in did not load. Check your network connection, then reload the page.';
    for (const slot of document.querySelectorAll('[data-google-button]')) {
        slot.replaceChildren(el('p', { className: 'google-button__error', text: message }));
    }
    setStep(0, 'error', message);
}

async function handleCredential(response) {
    resetSignInFlow();
    setStep(0, 'complete');
    setStep(1, 'active');

    const result = await request('POST', '/google-sign-in', { body: { token: response.credential }, auth: false });
    saveResponse(GOOGLE_SIGN_IN_ENDPOINT_ID, result);
    if (!result.ok) {
        setStep(1, 'error', errorMessage(result, 'The token exchange failed.'));
        return;
    }
    setStep(1, 'complete');

    startSession({ token: result.body.token, refreshToken: result.body.refresh_token });
    setStep(2, 'complete');
    announce(`Signed in as ${result.body.payload?.email ?? 'your account'}. Every endpoint is unlocked.`);
}

function setStep(index, status, errorText = null) {
    flowStatuses[index] = status;
    flowError = status === 'error' ? errorText : flowError;
    if (status === 'error' && errorText) {
        announce(`Sign-in step ${index + 1}, ${FLOW_STEPS[index].title}, failed: ${errorText}`);
    }
    notifyFlowChange();
}

function notifyFlowChange() {
    const flow = getSignInFlow();
    for (const listener of flowListeners) {
        listener(flow);
    }
}
