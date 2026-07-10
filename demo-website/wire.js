/**
 * The wire tape: a docked log of every HTTP call the bench makes,
 * each entry expandable to the full request and response.
 */

import { el, prettyJson, announce } from './ui.js';

const MAX_ENTRIES = 50;

let entriesEl;
let countEl;
let emptyEl;
let requestCount = 0;

export function initWire() {
    entriesEl = document.getElementById('wire-entries');
    countEl = document.getElementById('wire-count');

    emptyEl = el('p', {
        className: 'wire__empty',
        text: 'No requests yet — everything the bench sends to the service will appear here.',
    });
    entriesEl.append(emptyEl);

    document.getElementById('wire-clear').addEventListener('click', () => {
        entriesEl.replaceChildren(emptyEl);
        requestCount = 0;
        countEl.textContent = '0 requests';
        announce('Wire log cleared.');
    });

    const toggle = document.getElementById('wire-toggle');
    toggle.addEventListener('click', () => {
        const wire = document.getElementById('wire');
        const collapsed = wire.classList.toggle('wire--collapsed');
        toggle.setAttribute('aria-expanded', String(!collapsed));
        toggle.textContent = collapsed ? 'Expand' : 'Collapse';
    });
}

/** Appends one request entry (newest first). Called from api.js. */
export function recordEntry(entry) {
    emptyEl.remove();
    requestCount += 1;
    countEl.textContent = `${requestCount} request${requestCount === 1 ? '' : 's'}`;

    const failed = entry.status === null || entry.status >= 400;
    const statusText = entry.status === null ? 'network error' : String(entry.status);

    const summary = el('summary', {}, [
        el('span', { className: 'wire-entry__method', text: entry.method }),
        el('span', { className: 'wire-entry__path', text: entry.path }),
        el('span', {
            className: `wire-entry__status wire-entry__status--${failed ? 'error' : 'ok'}`,
            text: statusText,
        }),
        el('span', { className: 'wire-entry__ms', text: `${entry.durationMs} ms` }),
    ]);

    const body = el('div', { className: 'wire-entry__body' }, [
        el('p', { className: 'wire-entry__heading', text: 'Request headers' }),
        el('pre', {
            className: 'wire-entry__pre',
            text: Object.entries(entry.requestHeaders)
                .map(([name, value]) => `${name}: ${value}`)
                .join('\n') || '(none)',
        }),
        el('p', { className: 'wire-entry__heading', text: 'Request body' }),
        el('pre', {
            className: 'wire-entry__pre',
            text: entry.requestBody !== undefined ? prettyJson(entry.requestBody) : '(no body)',
        }),
        el('p', { className: 'wire-entry__heading', text: 'Response' }),
        el('pre', {
            className: 'wire-entry__pre',
            text: entry.error ?? (entry.responseBody !== null
                ? prettyJson(entry.responseBody)
                : '(empty response)'),
        }),
    ]);

    const details = el('details', {
        className: 'wire-entry',
        attrs: { 'data-side': entry.side },
    }, [summary, body]);

    entriesEl.prepend(details);
    while (entriesEl.children.length > MAX_ENTRIES) {
        entriesEl.lastElementChild.remove();
    }

    // Successful calls are announced by the panel that made them; the
    // wire only speaks up for failures so denials are never missed.
    if (failed) {
        announce(`${entry.method} ${entry.path} failed: ${statusText}.`);
    }
}
