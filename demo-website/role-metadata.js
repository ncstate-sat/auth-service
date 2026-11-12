/**
 * The role metadata panel: lists every role's alias and tags, and
 * saves or deletes them. These endpoints are not auth-protected yet,
 * so the panel works whether or not anyone is signed in.
 */

import { request, errorMessage } from './api.js';
import { el, announce, setStatus } from './ui.js';

let metadataByRole = new Map();

export function initRoleMetadata() {
    document.getElementById('load-role-metadata').addEventListener('click', () => loadRoleMetadata());
    document.getElementById('role-metadata-form').addEventListener('submit', handleSave);
    document.getElementById('role-metadata-form').addEventListener('reset', () => {
        setStatus('role-metadata-form-status', '');
    });
    document.getElementById('role-metadata-role').addEventListener('change', prefillFromKnownMetadata);
}

/** Rebuilds the tag checkboxes, keeping any that were checked and still exist. */
export function renderTagOptions(tagNames) {
    const checkedTags = new Set(checkedTagNames());
    document.getElementById('role-metadata-tags').replaceChildren(
        ...tagNames.map((name) => tagOption(name, checkedTags.has(name))),
    );
    showEmptyTagHint(!tagNames.length);
}

function tagOption(name, checked) {
    const checkbox = el('input', { attrs: { type: 'checkbox', name: 'role-metadata-tag', value: name } });
    checkbox.checked = checked;
    return el('label', { className: 'tag-option' }, [checkbox, el('span', { text: name })]);
}

function showEmptyTagHint(isEmpty) {
    const hint = document.getElementById('role-metadata-tags-empty');
    const fieldset = hint.closest('fieldset');
    hint.hidden = !isEmpty;
    if (isEmpty) {
        fieldset.setAttribute('aria-describedby', hint.id);
    } else {
        fieldset.removeAttribute('aria-describedby');
    }
}

function tagCheckboxes() {
    return [...document.querySelectorAll('#role-metadata-tags input[type="checkbox"]')];
}

function checkedTagNames() {
    return tagCheckboxes().filter((checkbox) => checkbox.checked).map((checkbox) => checkbox.value);
}

export async function loadRoleMetadata() {
    const result = await request('GET', '/role-metadata');
    if (!result.ok) {
        setStatus('role-metadata-status', errorMessage(result, 'Could not load role metadata.'), 'error');
        return;
    }

    const entries = result.body.role_metadata ?? [];
    metadataByRole = new Map(entries.map((entry) => [entry.role, entry]));
    document.getElementById('role-metadata-rows').replaceChildren(...entries.map(metadataRow));
    document.getElementById('role-metadata-table').hidden = !entries.length;
    setStatus(
        'role-metadata-status',
        entries.length
            ? `${entries.length} role${entries.length === 1 ? ' has' : 's have'} metadata.`
            : 'No roles have metadata yet. Add some with the form.',
    );
}

function metadataRow({ role, alias, tags }) {
    const editButton = el('button', {
        className: 'btn btn--ghost btn--small',
        text: 'Edit',
        attrs: { type: 'button', 'aria-label': `Edit metadata for ${role}` },
    });
    editButton.addEventListener('click', () => editMetadata(role));

    const deleteButton = el('button', {
        className: 'btn btn--ghost btn--small',
        text: 'Delete',
        attrs: { type: 'button', 'aria-label': `Delete metadata for ${role}` },
    });
    deleteButton.addEventListener('click', () => deleteMetadata(role));

    return el('tr', {}, [
        el('th', { text: role, attrs: { scope: 'row' } }),
        el('td', { text: alias ?? '(none)' }),
        el('td', { text: tags.length ? tags.join(', ') : '(none)' }),
        el('td', { className: 'metadata-table__actions' }, [editButton, deleteButton]),
    ]);
}

function fillForm(role, { alias, tags = [] } = {}) {
    document.getElementById('role-metadata-role').value = role;
    document.getElementById('role-metadata-alias').value = alias ?? '';
    const roleTags = new Set(tags);
    for (const checkbox of tagCheckboxes()) {
        checkbox.checked = roleTags.has(checkbox.value);
    }
}

function editMetadata(role) {
    fillForm(role, metadataByRole.get(role));
    setStatus('role-metadata-form-status', `Editing metadata for "${role}".`);
    document.getElementById('role-metadata-alias').focus();
    announce(`Editing metadata for ${role}. The form has been filled in.`);
}

/** Fills in a role's saved values so saving the form never clears them by accident. */
function prefillFromKnownMetadata() {
    const role = document.getElementById('role-metadata-role').value.trim();
    const existing = metadataByRole.get(role);
    if (!existing) {
        setStatus('role-metadata-form-status', role ? `"${role}" has no metadata yet.` : '');
        return;
    }
    fillForm(role, existing);
    setStatus('role-metadata-form-status', `Filled in the saved alias and tags for "${role}".`);
}

async function handleSave(event) {
    event.preventDefault();
    const role = document.getElementById('role-metadata-role').value.trim();
    const alias = document.getElementById('role-metadata-alias').value.trim();
    const tags = checkedTagNames();

    // The form shows the role's full metadata, so an empty alias is sent as null to clear it.
    const result = await request('POST', '/role-metadata', {
        body: { role, alias: alias || null, tags },
    });
    if (!result.ok) {
        setStatus('role-metadata-form-status', errorMessage(result, 'Could not save the metadata.'), 'error');
        return;
    }

    const message = result.status === 201
        ? `Created metadata for "${role}".`
        : `Updated metadata for "${role}".`;
    document.getElementById('role-metadata-form').reset();
    setStatus('role-metadata-form-status', message, 'ok');
    announce(message);
    await loadRoleMetadata();
}

async function deleteMetadata(role) {
    const result = await request('DELETE', `/role-metadata/${encodeURIComponent(role)}`);
    if (!result.ok) {
        setStatus('role-metadata-status', errorMessage(result, 'Could not delete the metadata.'), 'error');
        return;
    }

    await loadRoleMetadata();
    // The focused Delete button is gone with its row, so return focus to the list.
    document.getElementById('role-metadata-list-title').focus();
    announce(`Deleted metadata for ${role}.`);
}
