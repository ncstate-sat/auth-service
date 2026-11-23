/**
 * The wire log: a drawer docked to the bottom of the page listing every
 * HTTP call the bench makes, each expandable to the full request and response.
 */

import { el, prettyJson, announce, syncScrollRegion } from './dom.js';
import { describeStatus } from './api.js';

const MAX_ENTRIES = 50;

let requestCount = 0;

export function initWire() {
    document.getElementById('wire-toggle').addEventListener('click', toggleWire);
    document.getElementById('wire-clear').addEventListener('click', clearWire);
    keepScrollPaddingClearOfWire();
}

/** Adds one request to the top of the log. Called by api.js for every request. */
export function recordWireEntry(entry) {
    requestCount += 1;
    renderCount();
    document.getElementById('wire-empty').hidden = true;
    const time = formatClockTime(new Date());
    document.getElementById('wire-last').textContent = `${time}  ${entry.method} ${entry.path}  ${describeStatus(entry.status)}`;

    const entries = document.getElementById('wire-entries');
    entries.prepend(buildEntry(entry, time));
    const renderedEntries = entries.querySelectorAll('.wire-entry');
    if (renderedEntries.length > MAX_ENTRIES) {
        renderedEntries[renderedEntries.length - 1].remove();
    }
}

function toggleWire() {
    const toggle = document.getElementById('wire-toggle');
    const expanded = toggle.getAttribute('aria-expanded') !== 'true';
    toggle.setAttribute('aria-expanded', String(expanded));
    document.getElementById('wire-entries').hidden = !expanded;
}

function clearWire() {
    requestCount = 0;
    renderCount();
    for (const entry of document.querySelectorAll('.wire-entry')) {
        entry.remove();
    }
    document.getElementById('wire-empty').hidden = false;
    document.getElementById('wire-last').textContent = 'Requests appear here as you send them.';
    announce('Wire log cleared.');
}

function renderCount() {
    document.getElementById('wire-count').textContent = `${requestCount} request${requestCount === 1 ? '' : 's'}`;
}

function buildEntry(entry, time) {
    const failed = !entry.ok;
    const pathChildren = [entry.path];
    if (entry.usedCustomToken) {
        pathChildren.push(el('span', { className: 'wire-entry__actor', text: 'with a pasted token' }));
    }
    const summary = el('summary', {}, [
        el('span', { className: 'wire-entry__time', text: time }),
        el('span', { text: entry.method }),
        el('span', { className: 'wire-entry__path' }, pathChildren),
        el('span', {
            className: `wire-entry__status wire-entry__status--${failed ? 'error' : 'ok'}`,
            text: entry.status === null ? 'network error' : String(entry.status),
        }),
        el('span', { className: 'wire-entry__duration', text: `${entry.durationMs} ms` }),
    ]);

    const details = el('details', { className: 'wire-entry' }, [summary, buildEntryBody(entry)]);
    details.addEventListener('toggle', () => {
        for (const block of details.querySelectorAll('.wire-entry__pre')) {
            syncScrollRegion(block, `${entry.method} ${entry.path}, ${block.previousElementSibling.textContent}`);
        }
    });
    return details;
}

function buildEntryBody(entry) {
    const headers = Object.entries(entry.requestHeaders).map(([name, value]) => `${name}: ${value}`).join('\n');
    return el('div', { className: 'wire-entry__body' }, [
        ...buildSection('Request headers', headers || '(none)'),
        ...buildSection('Request body', entry.requestBody !== undefined ? prettyJson(entry.requestBody) : '(no body)'),
        ...buildSection('Response', describeResponse(entry)),
    ]);
}

function buildSection(heading, text) {
    return [
        el('p', { className: 'wire-entry__heading', text: heading }),
        el('pre', { className: 'wire-entry__pre', text }),
    ];
}

function describeResponse(entry) {
    if (entry.error) {
        return entry.error;
    }
    return entry.body !== null ? prettyJson(entry.body) : '(empty response)';
}

function formatClockTime(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
}

/** Keeps focused elements from scrolling under the sticky drawer (WCAG 2.4.11). */
function keepScrollPaddingClearOfWire() {
    const wire = document.getElementById('wire');
    new ResizeObserver(() => {
        document.documentElement.style.setProperty('--wire-height', `${wire.offsetHeight}px`);
    }).observe(wire);
}
