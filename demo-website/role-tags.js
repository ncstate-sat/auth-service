/**
 * The role tags panel: lists the tags consumers have registered, and
 * adds or deletes them. These endpoints are not auth-protected yet,
 * so the panel works whether or not anyone is signed in.
 */

import { request, errorMessage } from './api.js';
import { el, announce, setStatus } from './ui.js';

let notifyTagsLoaded = () => {};

/** onTagsLoaded receives the registered tag names every time they're reloaded. */
export function initRoleTags({ onTagsLoaded }) {
    notifyTagsLoaded = onTagsLoaded;
    document.getElementById('load-role-tags').addEventListener('click', () => loadRoleTags());
    document.getElementById('role-tag-form').addEventListener('submit', handleCreate);
}

export async function loadRoleTags() {
    const result = await request('GET', '/role-tags');
    if (!result.ok) {
        setStatus('role-tags-status', errorMessage(result, 'Could not load tags.'), 'error');
        return;
    }

    const tagNames = (result.body.role_tags ?? []).map((tag) => tag.name);
    document.getElementById('role-tags-rows').replaceChildren(...tagNames.map(tagRow));
    document.getElementById('role-tags-table').hidden = !tagNames.length;
    setStatus(
        'role-tags-status',
        tagNames.length
            ? `${tagNames.length} tag${tagNames.length === 1 ? ' is' : 's are'} registered.`
            : 'No tags are registered yet. Add one with the form.',
    );
    notifyTagsLoaded(tagNames);
}

function tagRow(name) {
    const deleteButton = el('button', {
        className: 'btn btn--ghost btn--small',
        text: 'Delete',
        attrs: { type: 'button', 'aria-label': `Delete tag ${name}` },
    });
    deleteButton.addEventListener('click', () => deleteTag(name));

    return el('tr', {}, [
        el('th', { text: name, attrs: { scope: 'row' } }),
        el('td', { className: 'metadata-table__actions' }, [deleteButton]),
    ]);
}

async function handleCreate(event) {
    event.preventDefault();
    const name = document.getElementById('role-tag-name').value.trim();

    const result = await request('POST', '/role-tags', { body: { name } });
    if (!result.ok) {
        setStatus('role-tag-form-status', errorMessage(result, 'Could not add the tag.'), 'error');
        return;
    }

    const message = `Added tag "${result.body.name}".`;
    document.getElementById('role-tag-form').reset();
    setStatus('role-tag-form-status', message, 'ok');
    announce(message);
    await loadRoleTags();
}

async function deleteTag(name) {
    const result = await request('DELETE', `/role-tags/${encodeURIComponent(name)}`);
    if (!result.ok) {
        const message = deleteErrorMessage(result);
        setStatus('role-tags-status', message, 'error');
        announce(message);
        return;
    }

    await loadRoleTags();
    // The focused Delete button is gone with its row, so return focus to the list.
    document.getElementById('role-tags-list-title').focus();
    announce(`Deleted tag ${name}.`);
}

function deleteErrorMessage(result) {
    const rolesWithTag = result.body?.detail?.roles;
    if (result.status === 409 && rolesWithTag) {
        return `${result.body.detail.message} Roles with this tag: ${rolesWithTag.join(', ')}.`;
    }
    return errorMessage(result, 'Could not delete the tag.');
}
