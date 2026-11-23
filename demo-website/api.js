/**
 * The single request pipeline. Every HTTP call the bench makes goes
 * through request() so it can carry a bearer token and land in the wire log.
 */

export const API_BASE = 'http://localhost:8000';

const STATUS_TEXT = {
    200: 'OK',
    201: 'Created',
    204: 'No Content',
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    409: 'Conflict',
    422: 'Unprocessable Content',
    500: 'Internal Server Error',
};

let sessionBearerToken = null;
let recorder = null;

export function setSessionBearerToken(token) {
    sessionBearerToken = token;
}

/** Registers the wire log's callback; it receives one entry per request. */
export function onRecord(callback) {
    recorder = callback;
}

/**
 * Performs a fetch and records it. Returns { ok, status, body, error, durationMs }.
 * Options: query (search params), body (sent as JSON), auth (attach a bearer
 * token, default true), and token (sent instead of the session's token).
 */
export async function request(method, path, { query, body, auth = true, token } = {}) {
    const url = buildUrl(path, query);
    const headers = buildHeaders({ hasBody: body !== undefined, bearer: auth ? token ?? sessionBearerToken : null });
    const entry = {
        method,
        path: url.pathname + url.search,
        usedCustomToken: Boolean(auth && token),
        requestHeaders: headers,
        requestBody: body,
    };

    const started = performance.now();
    const result = await sendAndRead(url, method, headers, body);
    result.durationMs = Math.round(performance.now() - started);

    recorder?.({ ...entry, ...result });
    return result;
}

export function buildUrl(path, query) {
    const url = new URL(path, API_BASE);
    for (const [key, value] of Object.entries(query ?? {})) {
        url.searchParams.set(key, value);
    }
    return url;
}

function buildHeaders({ hasBody, bearer }) {
    const headers = {};
    if (hasBody) {
        headers['Content-Type'] = 'application/json';
    }
    if (bearer) {
        headers['Authorization'] = `Bearer ${bearer}`;
    }
    return headers;
}

async function sendAndRead(url, method, headers, body) {
    try {
        const response = await fetch(url, {
            method,
            headers,
            body: body !== undefined ? JSON.stringify(body) : undefined,
        });
        return { ok: response.ok, status: response.status, body: await readBody(response) };
    } catch (error) {
        return { ok: false, status: null, body: null, error: `Could not reach ${url}: ${error.message}` };
    }
}

async function readBody(response) {
    const text = await response.text();
    try {
        return text ? JSON.parse(text) : null;
    } catch (error) {
        return text;
    }
}

export function describeStatus(status) {
    if (status === null) {
        return 'Network error';
    }
    return STATUS_TEXT[status] ? `${status} ${STATUS_TEXT[status]}` : String(status);
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
        return typeof body.detail === 'string' ? body.detail : describeValidationDetail(body.detail);
    }
    return `${fallback} (status ${result.status})`;
}

function describeValidationDetail(detail) {
    if (Array.isArray(detail)) {
        return detail.map((item) => item.msg ?? JSON.stringify(item)).join('; ');
    }
    return JSON.stringify(detail);
}
