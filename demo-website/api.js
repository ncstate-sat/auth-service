/**
 * The single request pipeline. Every HTTP call the bench makes goes
 * through request() so it can carry the bearer token and be recorded
 * on the wire tape.
 */

// Where the auth service is running.
export const API_BASE = 'http://localhost:8000';

// Endpoints served by controllers/authentication.py; everything else
// on this service is authorization.py. Drives the wire tape's hue.
const AUTHN_PATHS = new Set(['/google-sign-in', '/login', '/refresh-token']);

let bearerToken = null;
let recorder = null;

export function setBearerToken(token) {
    bearerToken = token;
}

/** Registers the wire tape's callback; receives one entry per request. */
export function onRecord(callback) {
    recorder = callback;
}

/**
 * Performs a fetch and records it. Returns { ok, status, body, error }.
 * Options: query (object of search params), body (JSON-serialized),
 * auth (attach the bearer token, default true).
 */
export async function request(method, path, { query, body, auth = true } = {}) {
    const url = new URL(path, API_BASE);
    for (const [key, value] of Object.entries(query ?? {})) {
        url.searchParams.set(key, value);
    }

    const headers = {};
    if (body !== undefined) {
        headers['Content-Type'] = 'application/json';
    }
    if (auth && bearerToken) {
        headers['Authorization'] = `Bearer ${bearerToken}`;
    }

    const entry = {
        method,
        path: url.pathname + url.search,
        side: AUTHN_PATHS.has(path) ? 'authn' : 'authz',
        requestHeaders: { ...headers },
        requestBody: body,
    };

    const started = performance.now();
    let result;
    try {
        const response = await fetch(url, {
            method,
            headers,
            body: body !== undefined ? JSON.stringify(body) : undefined,
        });
        let responseBody = null;
        const text = await response.text();
        try {
            responseBody = text ? JSON.parse(text) : null;
        } catch (error) {
            responseBody = text;
        }
        entry.status = response.status;
        entry.responseBody = responseBody;
        result = { ok: response.ok, status: response.status, body: responseBody };
    } catch (error) {
        entry.status = null;
        entry.error = `Could not reach ${url}: ${error.message}`;
        result = { ok: false, status: null, body: null, error: entry.error };
    }
    entry.durationMs = Math.round(performance.now() - started);

    recorder?.(entry);
    return result;
}

/** Pulls the most useful human-readable message out of a failed result. */
export function errorMessage(result, fallback = 'The request failed.') {
    if (result.error) {
        return result.error;
    }
    const body = result.body;
    if (body?.error) {
        return body.error;
    }
    if (body?.detail) {
        return typeof body.detail === 'string' ? body.detail : prettyDetail(body.detail);
    }
    return `${fallback} (status ${result.status})`;
}

function prettyDetail(detail) {
    // FastAPI validation errors arrive as a list of {loc, msg, type}.
    if (Array.isArray(detail)) {
        return detail.map((item) => item.msg ?? JSON.stringify(item)).join('; ');
    }
    return JSON.stringify(detail);
}
