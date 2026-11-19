/** Hash routing: #session is the start/session page, #<endpoint id> is an endpoint page. */

export const SESSION_ROUTE = 'session';

const routeListeners = [];

/** listener(route, { userNavigated }) */
export function onRouteChange(listener) {
    routeListeners.push(listener);
}

export function currentRoute() {
    return decodeURIComponent(location.hash.slice(1)) || SESSION_ROUTE;
}

export function initRouter() {
    window.addEventListener('hashchange', () => notifyRouteChange(true));
    notifyRouteChange(false);
}

function notifyRouteChange(userNavigated) {
    const route = currentRoute();
    for (const listener of routeListeners) {
        listener(route, { userNavigated });
    }
}
