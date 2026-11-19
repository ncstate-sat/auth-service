/** The response card beside the request form. */

import { describeStatus } from './api.js';
import { prettyJson, setCodeBlock } from './dom.js';

export function renderResponse(result) {
    const hasResult = result !== null;
    document.getElementById('response-meta').hidden = !hasResult;
    document.getElementById('response-body').hidden = !hasResult;
    document.getElementById('response-empty').hidden = hasResult;
    if (!hasResult) {
        return;
    }

    const status = document.getElementById('response-status');
    status.textContent = describeStatus(result.status);
    status.className = `status-pill status-pill--${result.ok ? 'ok' : 'error'}`;
    document.getElementById('response-duration').textContent = `${result.durationMs} ms`;
    setCodeBlock(document.getElementById('response-body'), describeBody(result));
}

function describeBody(result) {
    if (result.error) {
        return result.error;
    }
    return result.body === null ? '(empty response)' : prettyJson(result.body);
}
