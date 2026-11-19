/** The last response received per endpoint, kept so it survives navigating away and back. */

const responsesByEndpoint = new Map();
const changeListeners = [];

export function onResponseChange(listener) {
    changeListeners.push(listener);
}

export function getResponse(endpointId) {
    return responsesByEndpoint.get(endpointId) ?? null;
}

export function saveResponse(endpointId, result) {
    responsesByEndpoint.set(endpointId, result);
    notify(endpointId);
}

export function clearResponses() {
    responsesByEndpoint.clear();
    notify(null);
}

function notify(endpointId) {
    for (const listener of changeListeners) {
        listener(endpointId);
    }
}
