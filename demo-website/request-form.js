/** The request card: fields built from the endpoint definition, a live body preview, send, and copy as cURL. */

import { el, prettyJson, setCodeBlock } from './dom.js';
import { buildUrl } from './api.js';
import { buildCurlCommand } from './curl.js';
import { copyWithConfirmation } from './clipboard.js';
import { requestPath } from './endpoints.js';

const PREVIEW_TOKENS = { token: '<your auth token>', refreshToken: '<your refresh token>' };

const valuesByEndpoint = new Map();
let shownEndpoint = null;

export function initRequestForm({ onSend }) {
    document.getElementById('request-form').addEventListener('submit', (event) => {
        event.preventDefault();
        onSend(shownEndpoint, getValues(shownEndpoint));
    });
    document.getElementById('copy-curl').addEventListener('click', (event) => {
        const requestOptions = shownEndpoint.buildRequest(getValues(shownEndpoint), PREVIEW_TOKENS);
        copyWithConfirmation(event.currentTarget, buildCurlCommand(shownEndpoint, requestOptions));
    });
}

function getValues(endpoint) {
    if (!valuesByEndpoint.has(endpoint.id)) {
        valuesByEndpoint.set(endpoint.id, {});
    }
    return valuesByEndpoint.get(endpoint.id);
}

/** Fills empty email fields with the signed-in address. */
export function prefillSessionEmail(endpoints, email) {
    for (const endpoint of endpoints) {
        const values = getValues(endpoint);
        for (const field of endpoint.fields.filter((candidate) => candidate.prefillWithSessionEmail)) {
            values[field.name] ||= email;
        }
    }
}

export function renderRequestForm(endpoint) {
    shownEndpoint = endpoint;
    const noFieldsText = document.getElementById('request-no-fields');
    noFieldsText.hidden = endpoint.fields.length > 0;
    noFieldsText.textContent = endpoint.noFieldsText ?? '';
    document.getElementById('send-request').textContent = endpoint.sendLabel ?? 'Send request';
    document.getElementById('request-fields').replaceChildren(...endpoint.fields.map((field) => buildField(endpoint, field)));
    renderPreview();
}

function buildField(endpoint, field) {
    return field.type === 'choices' ? buildChoicesField(endpoint, field) : buildTextField(endpoint, field);
}

function buildTextField(endpoint, field) {
    const inputId = `field-${endpoint.id}-${field.name}`;
    const hintId = `${inputId}-hint`;
    const input = field.multiline
        ? el('textarea', { attrs: { rows: '3' } })
        : el('input', { attrs: { type: 'text', autocomplete: 'off' } });
    input.id = inputId;
    input.name = field.name;
    input.placeholder = field.placeholder ?? '';
    input.spellcheck = false;
    input.value = getValues(endpoint)[field.name] ?? '';
    input.addEventListener('input', () => {
        getValues(endpoint)[field.name] = input.value;
        renderPreview();
    });

    const children = [el('label', { text: field.label, attrs: { for: inputId } }), input];
    if (field.hint) {
        input.setAttribute('aria-describedby', hintId);
        children.push(el('p', { className: 'hint', text: field.hint, attrs: { id: hintId } }));
    }
    return el('div', { className: 'field' }, children);
}

/** A group of checkboxes whose value is the list of checked choice values. */
function buildChoicesField(endpoint, field) {
    const fieldsetId = `field-${endpoint.id}-${field.name}`;
    const hintId = `${fieldsetId}-hint`;
    const checkboxes = field.choices.map((choice) => buildChoiceCheckbox(endpoint, field, choice));
    const children = [el('legend', { text: field.label }), el('div', { className: 'choices' }, checkboxes)];
    const fieldset = el('fieldset', { className: 'field field--choices', attrs: { id: fieldsetId } });
    if (field.hint) {
        fieldset.setAttribute('aria-describedby', hintId);
        children.push(el('p', { className: 'hint', text: field.hint, attrs: { id: hintId } }));
    }
    fieldset.append(...children);
    return fieldset;
}

function buildChoiceCheckbox(endpoint, field, choice) {
    const checkboxId = `field-${endpoint.id}-${field.name}-${choice.value}`;
    const checkbox = el('input', { attrs: { type: 'checkbox', id: checkboxId, name: field.name, value: choice.value } });
    checkbox.checked = (getValues(endpoint)[field.name] ?? []).includes(choice.value);
    checkbox.addEventListener('change', () => {
        const checkedValues = new Set(getValues(endpoint)[field.name] ?? []);
        if (checkbox.checked) {
            checkedValues.add(choice.value);
        } else {
            checkedValues.delete(choice.value);
        }
        getValues(endpoint)[field.name] = field.choices
            .map((candidate) => candidate.value)
            .filter((value) => checkedValues.has(value));
        renderPreview();
    });
    return el('label', { className: 'choice', attrs: { for: checkboxId } }, [checkbox, choice.label]);
}

function renderPreview() {
    const requestOptions = shownEndpoint.buildRequest(getValues(shownEndpoint), PREVIEW_TOKENS);
    setCodeBlock(document.getElementById('request-preview'), describeRequest(requestOptions));
}

function describeRequest(requestOptions) {
    if (requestOptions.body !== undefined) {
        return prettyJson(requestOptions.body);
    }
    if (requestOptions.query || requestOptions.path) {
        const url = buildUrl(requestPath(shownEndpoint, requestOptions), requestOptions.query);
        return `No body. Sent as ${url.pathname}${url.search}`;
    }
    return 'No body.';
}
