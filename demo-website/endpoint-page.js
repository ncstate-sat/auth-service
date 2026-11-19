/** An endpoint's page: what it does, a request form, and the last response. */

import { request, describeStatus } from './api.js';
import { el, announce } from './dom.js';
import { onSessionChange, isSignedIn, getSession, startSession } from './session.js';
import { getResponse, saveResponse, onResponseChange } from './response-store.js';
import { onSignInFlowChange, getSignInFlow } from './google-sign-in.js';
import { initRequestForm, renderRequestForm } from './request-form.js';
import { renderResponse } from './response-panel.js';

const STEP_STATE_LABELS = { pending: 'Pending', active: 'In progress', complete: 'Done', error: 'Failed' };

let shownEndpoint = null;

export function initEndpointPage() {
    initRequestForm({ onSend: sendRequest });
    onSessionChange(() => shownEndpoint && renderSignInState(shownEndpoint));
    onResponseChange((endpointId) => {
        if (shownEndpoint && (endpointId === null || endpointId === shownEndpoint.id)) {
            renderResponse(getResponse(shownEndpoint.id));
        }
    });
    onSignInFlowChange(renderSignInFlow);
}

/** Shows the endpoint and returns its heading, for focusing. */
export function showEndpointPage(endpoint) {
    shownEndpoint = endpoint;
    renderHeader(endpoint);
    renderRequestForm(endpoint);
    renderSignInState(endpoint);
    renderResponse(getResponse(endpoint.id));
    document.getElementById('google-flow').hidden = !endpoint.usesGoogleButton;
    renderSignInFlow(getSignInFlow());
    document.getElementById('view-endpoint').hidden = false;
    return document.getElementById('endpoint-title');
}

export function hideEndpointPage() {
    shownEndpoint = null;
    document.getElementById('view-endpoint').hidden = true;
}

function renderHeader(endpoint) {
    document.title = `${endpoint.title} — Auth Service Demo Bench`;
    document.getElementById('endpoint-group').textContent = endpoint.group;
    document.getElementById('endpoint-title').textContent = endpoint.title;
    const method = document.getElementById('endpoint-method');
    method.textContent = endpoint.method;
    method.className = `method method--large method--${endpoint.method.toLowerCase()}`;
    document.getElementById('endpoint-path').textContent = endpoint.path;
    document.getElementById('endpoint-description').textContent = endpoint.description;
    document.getElementById('endpoint-auth').textContent = endpoint.auth;
    document.getElementById('endpoint-permission').textContent = endpoint.permission;
    document.getElementById('endpoint-more').textContent = endpoint.more;
}

function renderSignInState(endpoint) {
    const signedIn = isSignedIn();
    const locked = endpoint.requiresSignIn && !signedIn;
    document.getElementById('request-actions').hidden = locked || endpoint.usesGoogleButton;
    document.getElementById('sign-in-prompt').hidden = !locked;

    document.getElementById('google-sign-in-box').hidden = !endpoint.usesGoogleButton;
    document.querySelector('#google-sign-in-box [data-google-button]').hidden = signedIn;
    const signedInNote = document.getElementById('google-signed-in-note');
    signedInNote.hidden = !signedIn;
    signedInNote.textContent = signedIn
        ? `You're signed in as ${getSession().payload.email}. Sign out to run the exchange again.`
        : '';
}

function renderSignInFlow({ steps, error }) {
    document.getElementById('google-flow-steps').replaceChildren(...steps.map(buildFlowStep));
    const errorElement = document.getElementById('google-flow-error');
    errorElement.hidden = !error;
    errorElement.textContent = error ?? '';
}

function buildFlowStep(step, index) {
    return el('li', { className: `step step--${step.status}` }, [
        el('span', { className: 'step__number', text: String(index + 1), attrs: { 'aria-hidden': 'true' } }),
        el('div', {}, [
            el('p', { className: 'step__title' }, [
                step.title,
                el('span', { className: 'step__state', text: STEP_STATE_LABELS[step.status] }),
            ]),
            el('p', { className: 'hint' }, [el('code', { text: step.where })]),
        ]),
    ]);
}

async function sendRequest(endpoint, values) {
    const session = getSession();
    const requestOptions = endpoint.buildRequest(values, { token: session?.token, refreshToken: session?.refreshToken });
    const result = await request(endpoint.method, endpoint.path, requestOptions);
    saveResponse(endpoint.id, result);
    if (result.ok && endpoint.refreshesSessionWhenBlank && !values.token) {
        startSession({ token: result.body.token, refreshToken: result.body.refresh_token });
    }
    announce(`${endpoint.title}: ${describeStatus(result.status)}.`);
}
