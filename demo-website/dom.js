/** Small DOM building blocks shared by every view. */

export function announce(message) {
    const announcer = document.getElementById('status-announcer');
    announcer.textContent = '';
    // Clearing first makes screen readers repeat an identical message.
    requestAnimationFrame(() => {
        announcer.textContent = message;
    });
}

export function el(tag, { className, text, attrs } = {}, children = []) {
    const node = document.createElement(tag);
    if (className) {
        node.className = className;
    }
    if (text !== undefined) {
        node.textContent = text;
    }
    for (const [name, value] of Object.entries(attrs ?? {})) {
        node.setAttribute(name, value);
    }
    node.append(...children);
    return node;
}

export function prettyJson(value) {
    return JSON.stringify(value, null, 2);
}

export function setInlineStatus(elementId, message, tone = 'muted') {
    const status = document.getElementById(elementId);
    status.textContent = message ?? '';
    status.dataset.tone = tone;
}

/**
 * Makes a code block a focusable, named region when its content overflows,
 * so keyboard users can scroll it. Call after changing its content.
 */
export function syncScrollRegion(block, label = block.dataset.scrollLabel) {
    const overflows = block.scrollHeight > block.clientHeight + 1 || block.scrollWidth > block.clientWidth + 1;
    if (overflows) {
        block.tabIndex = 0;
        block.setAttribute('role', 'region');
        block.setAttribute('aria-label', label);
    } else {
        block.removeAttribute('tabindex');
        block.removeAttribute('role');
        block.removeAttribute('aria-label');
    }
}

export function setCodeBlock(block, text) {
    block.textContent = text;
    syncScrollRegion(block);
}
