/** The endpoint navigation: grouped links, the current page, and sign-in locks. */

import { el } from './dom.js';
import { ENDPOINTS, ENDPOINT_GROUPS } from './endpoints.js';
import { onRouteChange, currentRoute } from './router.js';
import { onSessionChange, isSignedIn } from './session.js';

const LOCK_ICON_PATHS = '<rect x="5" y="11" width="14" height="10" rx="2"></rect><path d="M8 11V7a4 4 0 0 1 8 0v4"></path>';

export function initSidebar() {
    document.getElementById('endpoint-nav-groups').replaceChildren(...ENDPOINT_GROUPS.map(buildNavGroup));
    onRouteChange(markCurrentPage);
    onSessionChange(updateLocks);
    updateLocks();
}

function buildNavGroup(groupName) {
    const headingId = `nav-group-${groupName.toLowerCase().replace(/\s+/g, '-')}`;
    const links = ENDPOINTS
        .filter((endpoint) => endpoint.group === groupName)
        .map((endpoint) => el('li', {}, [buildNavLink(endpoint)]));
    return el('div', {}, [
        el('h2', { className: 'nav-group__title', text: groupName, attrs: { id: headingId } }),
        el('ul', { className: 'nav-group__list', attrs: { 'aria-labelledby': headingId } }, links),
    ]);
}

function buildNavLink(endpoint) {
    const link = el('a', { className: 'nav-item', attrs: { href: `#${endpoint.id}`, 'data-route': endpoint.id } }, [
        el('span', { className: `method method--${endpoint.method.toLowerCase()}`, text: endpoint.method }),
        el('span', { className: 'nav-item__title', text: endpoint.title }),
    ]);
    if (endpoint.requiresSignIn) {
        link.append(buildLockIndicator());
    }
    return link;
}

function buildLockIndicator() {
    const indicator = el('span', { className: 'nav-item__lock', attrs: { 'data-lock': '' } });
    indicator.innerHTML = `<svg aria-hidden="true" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">${LOCK_ICON_PATHS}</svg>`;
    indicator.append(el('span', { className: 'visually-hidden', text: '(sign in required)' }));
    return indicator;
}

function markCurrentPage(route = currentRoute()) {
    for (const link of document.querySelectorAll('.sidebar [data-route]')) {
        if (link.dataset.route === route) {
            link.setAttribute('aria-current', 'page');
            scrollSidebarToShow(link);
        } else {
            link.removeAttribute('aria-current');
        }
    }
}

/** Scrolls only the sidebar, never the page, so the current link is visible above the wire log. */
function scrollSidebarToShow(link) {
    const sidebar = link.closest('.sidebar');
    const sidebarBox = sidebar.getBoundingClientRect();
    const visibleBottom = Math.min(sidebarBox.bottom, document.getElementById('wire').getBoundingClientRect().top);
    const linkBox = link.getBoundingClientRect();
    const breathingRoom = 12;
    if (linkBox.top < sidebarBox.top) {
        sidebar.scrollTop -= sidebarBox.top - linkBox.top + breathingRoom;
    } else if (linkBox.bottom > visibleBottom) {
        sidebar.scrollTop += linkBox.bottom - visibleBottom + breathingRoom;
    }
}

function updateLocks() {
    const signedIn = isSignedIn();
    for (const lock of document.querySelectorAll('.sidebar [data-lock]')) {
        lock.hidden = signedIn;
    }
    document.getElementById('session-nav-label').textContent = signedIn ? 'Your session' : 'Start here';
}
