/**
 * The roles side of the workbench: the known-roles directory, role
 * creation, and the role detail panel (permissions, inheritance,
 * effective permissions, accounts holding the role).
 */

import { request, errorMessage } from './api.js';
import { el, announce, setStatus } from './ui.js';

let knownRoles = [];
let currentRole = null;

export function initRoles() {
    document.getElementById('load-roles').addEventListener('click', () => loadRoles());
    document.getElementById('create-role-form').addEventListener('submit', handleCreateRole);
    document.getElementById('create-role-add-row').addEventListener('click', addPermissionRow);
    document.getElementById('create-role-perms').addEventListener('click', handleRemoveRowClick);
    document.getElementById('role-lookup-form').addEventListener('submit', (event) => {
        event.preventDefault();
        openRole(document.getElementById('role-lookup-input').value.trim());
    });
    document.getElementById('add-perm-form').addEventListener('submit', handleAddPermission);
    document.getElementById('add-parent-form').addEventListener('submit', handleAddParent);
    document.getElementById('load-role-accounts').addEventListener('click', loadRoleAccounts);
    updateRowRemoveButtons();
}

export function resetRoles() {
    knownRoles = [];
    currentRole = null;
    document.getElementById('known-roles').replaceChildren();
    document.getElementById('roles-list').replaceChildren();
    document.getElementById('role-detail').hidden = true;
    document.getElementById('role-detail-empty').hidden = false;
    for (const statusId of ['roles-status', 'create-role-status', 'perms-status', 'parents-status', 'role-accounts-status']) {
        setStatus(statusId, '');
    }
    document.getElementById('create-role-form').reset();
    document.getElementById('role-lookup-form').reset();
}

/* ── Known roles directory ─────────────────────────────────────── */

export async function loadRoles() {
    const result = await request('GET', '/roles');
    if (!result.ok) {
        setStatus('roles-status', errorMessage(result, 'Could not load roles.'), 'error');
        return;
    }
    knownRoles = result.body.roles ?? [];

    document.getElementById('known-roles').replaceChildren(
        ...knownRoles.map((role) => el('option', { attrs: { value: role } })),
    );
    document.getElementById('roles-list').replaceChildren(
        ...knownRoles.map((role) => el('li', {}, [roleButton(role)])),
    );
    setStatus(
        'roles-status',
        knownRoles.length
            ? `${knownRoles.length} known role${knownRoles.length === 1 ? '' : 's'}.`
            : 'No roles are known yet — create one below.',
    );
}

function roleButton(role) {
    const button = el('button', {
        className: 'role-list__button',
        text: role,
        attrs: { type: 'button', 'aria-pressed': String(role === currentRole) },
    });
    button.addEventListener('click', () => openRole(role));
    return button;
}

function markSelectedRole() {
    for (const button of document.querySelectorAll('.role-list__button')) {
        button.setAttribute('aria-pressed', String(button.textContent === currentRole));
    }
}

/* ── Create a role ─────────────────────────────────────────────── */

function buildPermissionRow() {
    const removeButton = el('button', {
        className: 'btn btn--ghost btn--small perm-row__remove',
        text: 'Remove',
        attrs: { type: 'button', 'aria-label': 'Remove this permission row' },
    });
    return el('div', { className: 'perm-row' }, [
        el('label', { className: 'field field--grow' }, [
            el('span', { className: 'field__label', text: 'Object (resource)' }),
            el('input', { attrs: { type: 'text', name: 'obj', required: '', autocomplete: 'off', placeholder: 'member' } }),
        ]),
        el('label', { className: 'field' }, [
            el('span', { className: 'field__label', text: 'Action' }),
            el('input', { attrs: { type: 'text', name: 'act', required: '', autocomplete: 'off', placeholder: 'read' } }),
        ]),
        removeButton,
    ]);
}

function addPermissionRow() {
    const rows = document.getElementById('create-role-perms');
    rows.append(buildPermissionRow());
    updateRowRemoveButtons();
    rows.lastElementChild.querySelector('input').focus();
}

function handleRemoveRowClick(event) {
    const removeButton = event.target.closest('.perm-row__remove');
    if (!removeButton) {
        return;
    }
    removeButton.closest('.perm-row').remove();
    updateRowRemoveButtons();
}

function updateRowRemoveButtons() {
    const rows = document.querySelectorAll('#create-role-perms .perm-row');
    for (const row of rows) {
        row.querySelector('.perm-row__remove').disabled = rows.length === 1;
    }
}

function resetPermissionRows() {
    const rows = document.querySelectorAll('#create-role-perms .perm-row');
    for (const [index, row] of rows.entries()) {
        if (index > 0) {
            row.remove();
        }
    }
    updateRowRemoveButtons();
}

async function handleCreateRole(event) {
    event.preventDefault();
    const role = document.getElementById('create-role-name').value.trim();
    const addPermissions = [...document.querySelectorAll('#create-role-perms .perm-row')].map((row) => ({
        obj: row.querySelector('input[name="obj"]').value.trim(),
        act: row.querySelector('input[name="act"]').value.trim(),
    }));

    const result = await request('PUT', '/update-role-permissions', {
        body: { role, add_permissions: addPermissions },
    });
    if (!result.ok) {
        setStatus('create-role-status', errorMessage(result, 'Could not create the role.'), 'error');
        return;
    }

    const count = addPermissions.length;
    setStatus('create-role-status', `Created role "${role}" with ${count} permission${count === 1 ? '' : 's'}.`, 'ok');
    announce(`Created role ${role}.`);
    document.getElementById('create-role-form').reset();
    resetPermissionRows();
    await loadRoles();
    await openRole(role);
}

/* ── Role detail ───────────────────────────────────────────────── */

async function openRole(role) {
    if (!role) {
        return;
    }
    currentRole = role;
    document.getElementById('role-lookup-input').value = role;
    document.getElementById('role-detail-empty').hidden = true;
    document.getElementById('role-detail').hidden = false;
    document.getElementById('role-detail-name').textContent = role;
    document.getElementById('role-accounts-list').replaceChildren();
    setStatus('role-accounts-status', '');
    markSelectedRole();
    announce(`Opened role ${role}.`);
    await refreshRoleData();
}

async function refreshRoleData() {
    const role = currentRole;

    const permsResult = await request('GET', '/role-permissions', { query: { role } });
    const permsList = document.getElementById('perms-list');
    const directKeys = new Set();
    if (!permsResult.ok) {
        permsList.replaceChildren();
        setStatus('perms-status', errorMessage(permsResult, 'Could not read permissions.'), 'error');
    } else {
        const permissions = permsResult.body.permissions ?? [];
        for (const { obj, act } of permissions) {
            directKeys.add(`${obj}:${act}`);
        }
        permsList.replaceChildren(...permissions.map(({ obj, act }) => tupleRow(
            `p, ${role}, ${obj}, ${act}`,
            `Remove permission ${obj}:${act} from ${role}`,
            () => removePermission(obj, act),
        )));
        setStatus(
            'perms-status',
            permissions.length
                ? `${permissions.length} direct permission${permissions.length === 1 ? '' : 's'}.`
                : 'No direct permissions. A role with no permissions and no dependents drops out of /roles.',
        );
    }

    const inheritanceResult = await request('GET', '/role-inheritance', { query: { role } });
    const parentsList = document.getElementById('parents-list');
    const effectiveList = document.getElementById('effective-list');
    if (!inheritanceResult.ok) {
        parentsList.replaceChildren();
        effectiveList.replaceChildren();
        setStatus('parents-status', errorMessage(inheritanceResult, 'Could not read inheritance.'), 'error');
        return;
    }

    const parents = inheritanceResult.body.inherited_roles ?? [];
    parentsList.replaceChildren(...parents.map((parent) => tupleRow(
        `g, ${role}, ${parent}`,
        `Stop ${role} inheriting from ${parent}`,
        () => removeParent(parent),
    )));
    setStatus(
        'parents-status',
        parents.length
            ? `Inherits from ${parents.length} role${parents.length === 1 ? '' : 's'}.`
            : 'Inherits from no other roles.',
    );

    const effective = inheritanceResult.body.effective_permissions ?? [];
    effectiveList.replaceChildren(...effective.map(({ obj, act }) => {
        const direct = directKeys.has(`${obj}:${act}`);
        return el('li', { className: 'tuple' }, [
            el('span', { className: 'tuple__text', text: `${obj}:${act}` }),
            el('span', {
                className: `tag ${direct ? 'tag--direct' : 'tag--inherited'}`,
                text: direct ? 'direct' : 'inherited',
            }),
        ]);
    }));
    if (!effective.length) {
        effectiveList.replaceChildren(el('li', { className: 'tuple' }, [
            el('span', { className: 'tuple__text', text: '(none)' }),
        ]));
    }
}

function tupleRow(text, removeLabel, onRemove) {
    const removeButton = el('button', {
        className: 'btn btn--ghost btn--small',
        text: 'Remove',
        attrs: { type: 'button', 'aria-label': removeLabel },
    });
    removeButton.addEventListener('click', onRemove);
    return el('li', { className: 'tuple' }, [
        el('span', { className: 'tuple__text', text }),
        removeButton,
    ]);
}

async function handleAddPermission(event) {
    event.preventDefault();
    const obj = document.getElementById('add-perm-obj').value.trim();
    const act = document.getElementById('add-perm-act').value.trim();
    const result = await request('PUT', '/update-role-permissions', {
        body: { role: currentRole, add_permissions: [{ obj, act }] },
    });
    if (!result.ok) {
        setStatus('perms-status', errorMessage(result, 'Could not add the permission.'), 'error');
        return;
    }
    announce(`Added permission ${obj}:${act} to ${currentRole}.`);
    document.getElementById('add-perm-form').reset();
    await refreshRoleData();
    await loadRoles();
}

async function removePermission(obj, act) {
    const result = await request('PUT', '/update-role-permissions', {
        body: { role: currentRole, remove_permissions: [{ obj, act }] },
    });
    if (!result.ok) {
        setStatus('perms-status', errorMessage(result, 'Could not remove the permission.'), 'error');
        return;
    }
    announce(`Removed permission ${obj}:${act} from ${currentRole}.`);
    await refreshRoleData();
    await loadRoles();
}

async function handleAddParent(event) {
    event.preventDefault();
    const parent = document.getElementById('add-parent-input').value.trim();
    const result = await request('PUT', '/update-role-inheritance', {
        body: { role: currentRole, add_inherited_roles: [parent] },
    });
    if (!result.ok) {
        // Cycles are rejected by the service with a descriptive 400.
        setStatus('parents-status', errorMessage(result, 'Could not add the inheritance.'), 'error');
        return;
    }
    announce(`${currentRole} now inherits from ${parent}.`);
    document.getElementById('add-parent-form').reset();
    await refreshRoleData();
    await loadRoles();
}

async function removeParent(parent) {
    const result = await request('PUT', '/update-role-inheritance', {
        body: { role: currentRole, remove_inherited_roles: [parent] },
    });
    if (!result.ok) {
        setStatus('parents-status', errorMessage(result, 'Could not remove the inheritance.'), 'error');
        return;
    }
    announce(`${currentRole} no longer inherits from ${parent}.`);
    await refreshRoleData();
    await loadRoles();
}

async function loadRoleAccounts() {
    const result = await request('GET', '/role-accounts', { query: { role: currentRole } });
    const list = document.getElementById('role-accounts-list');
    if (!result.ok) {
        list.replaceChildren();
        setStatus('role-accounts-status', errorMessage(result, 'Could not load accounts.'), 'error');
        return;
    }
    const accounts = result.body.accounts ?? [];
    list.replaceChildren(...accounts.map((account) => el('li', {}, [
        el('strong', { text: account.email }),
        el('span', {
            className: 'account__roles',
            text: ` — roles: ${(account.roles ?? []).join(', ') || '(none)'}`,
        }),
    ])));
    setStatus(
        'role-accounts-status',
        accounts.length
            ? `${accounts.length} account${accounts.length === 1 ? '' : 's'} hold this role.`
            : 'No accounts hold this role.',
    );
}
