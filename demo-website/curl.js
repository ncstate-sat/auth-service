import { buildUrl } from './api.js';
import { requestPath } from './endpoints.js';

/** A copy-pasteable cURL command for an endpoint request, with $TOKEN standing in for the bearer token. */
export function buildCurlCommand(endpoint, requestOptions) {
    const url = buildUrl(requestPath(endpoint, requestOptions), requestOptions.query);
    const lines = [`curl -X ${endpoint.method} "${url}"`];
    if (requestOptions.auth !== false) {
        lines.push('-H "Authorization: Bearer $TOKEN"');
    }
    if (requestOptions.body !== undefined) {
        lines.push('-H "Content-Type: application/json"');
        lines.push(`-d '${JSON.stringify(requestOptions.body).replace(/'/g, "'\\''")}'`);
    }
    return lines.join(' \\\n  ');
}
