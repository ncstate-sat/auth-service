/**
 * The accounts side of the workbench: inspect an account's roles and
 * flattened permissions, and add or remove roles on an account.
 */

import { request, errorMessage } from './api.js';
import { el, announce, setStatus } from './ui.js';

export function initAccounts() {
    document.getElementById('inspect-form').addEventListener('submit', handleInspect);
    document.getElementById('modify-form').addEventListener('submit', handleModify);
}

export function resetAccounts() {
    document.getElementById('inspect-form').reset();
    document.getElementById('modify-form').reset();
    document.getElementById('inspect-result').hidden = true;
    document.getElementById('modify-result').hidden = true;
    setStatus('inspect-status', '');
    setStatus('modify-status', '');
}

/** Prefills empty email inputs with the signed-in address. */
export function prefillEmail(email) {
    for (const inputId of ['inspect-email', 'modify-email']) {
        const input = document.getElementById(inputId);
        if (!input.value) {
            input.value = email ?? '';
        }
    }
}

async function handleInspect(event) {
    event.preventDefault();
    const email = document.getElementById('inspect-email').value.trim();
    const result = await request('GET', '/account', { query: { email } });

    if (!result.ok) {
        document.getElementById('inspect-result').hidden = true;
        setStatus('inspect-status', errorMessage(result, 'Could not read the account.'), 'error');
        return;
    }

    const account = result.body;
    document.getElementById('inspect-roles').replaceChildren(
        ...(account.roles ?? []).map((role) => el('span', { className: 'chip', text: role })),
    );
    if (!(account.roles ?? []).length) {
        document.getElementById('inspect-roles').replaceChildren(
            el('span', { className: 'hint', text: '(no roles)' }),
        );
    }

    const permissions = account.permissions ?? [];
    document.getElementById('inspect-perms').replaceChildren(
        ...(permissions.length ? permissions : ['(none)']).map((permission) =>
            el('li', { className: 'tuple' }, [
                el('span', { className: 'tuple__text', text: permission }),
            ])),
    );

    document.getElementById('inspect-result').hidden = false;
    setStatus('inspect-status', `Loaded ${account.email}.`, 'ok');
    announce(`Loaded account ${account.email}.`);
}

async function handleModify(event) {
    event.preventDefault();
    const intent = event.submitter?.value ?? 'add';
    const email = document.getElementById('modify-email').value.trim();
    const role = document.getElementById('modify-role').value.trim();

    const body = { email };
    body[intent === 'remove' ? 'remove_roles' : 'add_roles'] = [role];

    const result = await request('PUT', '/update-account-roles', { body });
    if (!result.ok) {
        document.getElementById('modify-result').hidden = true;
        setStatus('modify-status', errorMessage(result, 'Could not change the account roles.'), 'error');
        return;
    }

    const account = result.body.account ?? {};
    document.getElementById('modify-roles').replaceChildren(
        ...(account.roles ?? []).map((accountRole) => el('span', { className: 'chip', text: accountRole })),
    );
    if (!(account.roles ?? []).length) {
        document.getElementById('modify-roles').replaceChildren(
            el('span', { className: 'hint', text: '(no roles)' }),
        );
    }
    document.getElementById('modify-result').hidden = false;

    const message = intent === 'remove'
        ? `Removed role "${role}" from ${email}.`
        : `Added role "${role}" to ${email}.`;
    setStatus('modify-status', message, 'ok');
    announce(message);
}
