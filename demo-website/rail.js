/**
 * Shared helpers for a station rail: an <ol> of numbered steps, each
 * with a status badge, an inline error, and JWT artifacts.
 *
 * Element IDs follow a convention keyed by idPrefix:
 *   ${idPrefix}station-${n}         the station <li>
 *   ${idPrefix}station-error-${n}   its inline error
 * and, per JWT artifact prefix: raw-${prefix}, details-${prefix},
 * decoded-${prefix}-header, decoded-${prefix}-payload.
 */

import { decodeJwt, prettyJson, announce, syncScrollRegion } from './ui.js';

const STATUS_LABELS = {
    pending: 'Pending',
    active: 'In progress',
    complete: 'Complete',
    error: 'Error',
};

/**
 * Returns setStatus(stationNumber, status, errorText, { silent }) for one
 * rail. announcePrefix and titles make up the screen reader announcement,
 * e.g. "Step 2, Token exchange: Complete."
 */
export function createRail(idPrefix, titles, announcePrefix = 'Step') {
    return function setStationStatus(stationNumber, status, errorText, { silent = false } = {}) {
        const station = document.getElementById(`${idPrefix}station-${stationNumber}`);
        station.classList.remove('station--pending', 'station--active', 'station--complete', 'station--error');
        station.classList.add(`station--${status}`);

        const badge = station.querySelector('.status-badge--step');
        badge.classList.remove('status-badge--pending', 'status-badge--active', 'status-badge--complete', 'status-badge--error');
        badge.classList.add(`status-badge--${status}`);
        badge.textContent = STATUS_LABELS[status];

        const errorEl = document.getElementById(`${idPrefix}station-error-${stationNumber}`);
        if (status === 'error' && errorText) {
            errorEl.textContent = errorText;
            errorEl.hidden = false;
        } else {
            errorEl.hidden = true;
        }

        if (!silent) {
            const detail = status === 'error' && errorText ? ` ${errorText}` : '';
            announce(`${announcePrefix} ${stationNumber}, ${titles[stationNumber]}: ${STATUS_LABELS[status]}.${detail}`);
        }
    };
}

/** The artifact's visible label (e.g. "Auth token"), for naming its code blocks. */
function artifactLabel(prefix) {
    const row = document.getElementById(`raw-${prefix}`).previousElementSibling;
    return row?.querySelector('.artifact__label')?.textContent.trim() ?? prefix;
}

/** Shows a raw JWT and, if it decodes, its header and payload. */
export function renderJwt(prefix, token) {
    const label = artifactLabel(prefix);
    const raw = document.getElementById(`raw-${prefix}`);
    raw.textContent = token;
    syncScrollRegion(raw, label);

    const decoded = decodeJwt(token);
    const details = document.getElementById(`details-${prefix}`);
    if (decoded) {
        document.getElementById(`decoded-${prefix}-header`).textContent = prettyJson(decoded.header);
        document.getElementById(`decoded-${prefix}-payload`).textContent = prettyJson(decoded.payload);
        details.hidden = false;
        // The decoded blocks only have a size once their <details> is open.
        details.ontoggle = () => {
            syncScrollRegion(document.getElementById(`decoded-${prefix}-header`), `${label}, decoded header`);
            syncScrollRegion(document.getElementById(`decoded-${prefix}-payload`), `${label}, decoded payload`);
        };
    } else {
        details.hidden = true;
    }
    return decoded;
}

/** Clears a JWT artifact back to empty. */
export function clearJwt(prefix) {
    const raw = document.getElementById(`raw-${prefix}`);
    raw.textContent = '';
    syncScrollRegion(raw, '');
    const details = document.getElementById(`details-${prefix}`);
    details.hidden = true;
    details.open = false;
}
