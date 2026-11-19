/** Shows the page for the current route and moves focus to its heading when you navigate. */

import { findEndpoint } from './endpoints.js';
import { onRouteChange, currentRoute, SESSION_ROUTE } from './router.js';
import { onSessionChange } from './session.js';
import { showSessionPage, hideSessionPage } from './session-page.js';
import { showEndpointPage, hideEndpointPage } from './endpoint-page.js';

const DEFAULT_TITLE = 'Auth Service — Demo Bench';

let wasSignedIn = false;

export function initPageSwitcher() {
    onRouteChange((route, { userNavigated }) => showPage(route, userNavigated));
    onSessionChange((session) => {
        const signedIn = session !== null;
        if (signedIn === wasSignedIn) {
            return;
        }
        wasSignedIn = signedIn;
        // Signing in or out hides the control that had focus, so move it to the page heading.
        showPage(currentRoute(), true);
    });
}

function showPage(route, moveFocus) {
    const endpoint = route === SESSION_ROUTE ? null : findEndpoint(route);
    let heading;
    if (endpoint) {
        hideSessionPage();
        heading = showEndpointPage(endpoint);
    } else {
        hideEndpointPage();
        document.title = DEFAULT_TITLE;
        heading = showSessionPage();
    }
    if (moveFocus) {
        heading.focus();
    }
}
