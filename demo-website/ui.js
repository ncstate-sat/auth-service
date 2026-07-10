/**
 * Shared DOM and formatting helpers.
 */

/** Announces a message to screen readers via the polite live region. */
export function announce(message) {
    document.getElementById('status-announcer').textContent = message;
}

/** Creates an element with a class, text content, and attributes. */
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
    for (const child of children) {
        node.append(child);
    }
    return node;
}

export function prettyJson(value) {
    return JSON.stringify(value, null, 2);
}

function base64UrlDecode(segment) {
    let base64 = segment.replace(/-/g, '+').replace(/_/g, '/');
    const paddingNeeded = base64.length % 4;
    if (paddingNeeded) {
        base64 += '='.repeat(4 - paddingNeeded);
    }
    return atob(base64);
}

/** Decodes a JWT into { header, payload }, or null if it isn't one. */
export function decodeJwt(token) {
    const parts = (token ?? '').split('.');
    if (parts.length < 2) {
        return null;
    }
    try {
        return {
            header: JSON.parse(base64UrlDecode(parts[0])),
            payload: JSON.parse(base64UrlDecode(parts[1])),
        };
    } catch (error) {
        return null;
    }
}

/**
 * Sets an inline status line. Tone is one of 'muted' | 'ok' | 'error'
 * and is reinforced by the message text, never by color alone.
 */
export function setStatus(elementId, message, tone = 'muted') {
    const status = document.getElementById(elementId);
    status.textContent = message ?? '';
    status.dataset.tone = tone;
}

/** Wires up every [data-copy-target] button through one delegated listener. */
export function initCopyButtons() {
    document.addEventListener('click', (event) => {
        const button = event.target.closest('[data-copy-target]');
        if (!button) {
            return;
        }
        const target = document.getElementById(button.dataset.copyTarget);
        if (!target || !target.textContent) {
            return;
        }
        navigator.clipboard.writeText(target.textContent).then(() => {
            const originalLabel = button.textContent;
            button.textContent = 'Copied!';
            announce('Copied to clipboard.');
            setTimeout(() => {
                button.textContent = originalLabel;
            }, 1500);
        });
    });
}
