/** Endpoints for role metadata (alias, tags, description) and the registry of tags roles can carry. */

import { roleField, filledText } from './endpoint-fields.js';
import { parseLines } from './field-parsing.js';

const tagNameField = (placeholder) => ({ name: 'name', label: 'Tag name', placeholder, hint: 'Case-sensitive.' });
const rolePath = (values) => `/role-metadata/${encodeURIComponent(values.role ?? '')}`;
const tagPath = (values) => `/role-tags/${encodeURIComponent(values.name ?? '')}`;

const CLEARABLE_METADATA_FIELDS = [
    { value: 'alias', label: 'Alias' },
    { value: 'tags', label: 'Tags' },
    { value: 'description', label: 'Description' },
];

export const ROLE_METADATA_ENDPOINTS = [
    {
        id: 'list-role-metadata',
        group: 'Role metadata',
        method: 'GET',
        path: '/role-metadata',
        title: 'List role metadata',
        description: 'The alias, tags and description of every role that has metadata, sorted by role.',
        auth: 'Bearer token',
        permission: 'read on each role (roles you can’t read are left out)',
        requiresSignIn: true,
        more: 'Metadata lives in its own collection, apart from Casbin, so it never changes a role’s permissions, inheritance or accounts. Roles without metadata don’t appear.',
        fields: [{ name: 'tag', label: 'Only roles with this tag', placeholder: 'Feature', hint: 'Optional. Leave blank for every role.' }],
        buildRequest: (values) => {
            const tag = filledText(values.tag);
            return tag ? { query: { tag } } : {};
        },
    },
    {
        id: 'role-metadata',
        group: 'Role metadata',
        method: 'GET',
        path: '/role-metadata/{role}',
        title: 'Get role metadata',
        description: 'One role’s alias, tags and description.',
        auth: 'Bearer token',
        permission: 'read on the role',
        requiresSignIn: true,
        more: 'Returns 404 when the role has no metadata. The permission is checked first, so a 403 doesn’t reveal whether metadata exists.',
        fields: [roleField('security-liaison')],
        buildRequest: (values) => ({ path: rolePath(values) }),
    },
    {
        id: 'save-role-metadata',
        group: 'Role metadata',
        method: 'POST',
        path: '/role-metadata',
        title: 'Save role metadata',
        description: 'Creates a role’s metadata, or updates it if the role already has some.',
        auth: 'Bearer token',
        permission: 'roleupdate on the role',
        requiresSignIn: true,
        more: 'Returns 201 when created and 200 when updated. Fields you leave blank keep their current value. Sent tags replace the role’s whole tag list. Aliases are unique across roles, ignoring case (409 if taken), and tags must already be registered under Role tags (422 if not). The role doesn’t need to exist in Casbin yet.',
        fields: [
            roleField('security-liaison'),
            { name: 'alias', label: 'Alias', placeholder: 'Security Liaison', hint: 'A display name. Leave blank to keep the current one.' },
            { name: 'tags', label: 'Tags', multiline: true, placeholder: 'User', hint: 'One tag per line. Replaces the role’s tags. Leave blank to keep them.' },
            { name: 'description', label: 'Description', multiline: true, placeholder: 'Coordinates security reviews', hint: 'Leave blank to keep the current one.' },
            {
                name: 'clear',
                label: 'Clear these fields',
                type: 'choices',
                choices: CLEARABLE_METADATA_FIELDS,
                hint: 'A checked field is cleared, even if you typed a value for it.',
            },
        ],
        buildRequest: (values) => ({ body: buildSaveMetadataBody(values) }),
    },
    {
        id: 'delete-role-metadata',
        group: 'Role metadata',
        method: 'DELETE',
        path: '/role-metadata/{role}',
        title: 'Delete role metadata',
        description: 'Removes a role’s alias, tags and description.',
        auth: 'Bearer token',
        permission: 'roleupdate on the role',
        requiresSignIn: true,
        more: 'Returns 204 with no body. The role itself and its Casbin permissions, inheritance and accounts are untouched.',
        fields: [roleField('security-liaison')],
        buildRequest: (values) => ({ path: rolePath(values) }),
    },
];

export const ROLE_TAG_ENDPOINTS = [
    {
        id: 'role-tags',
        group: 'Role tags',
        method: 'GET',
        path: '/role-tags',
        title: 'List tags',
        description: 'Every registered tag, sorted by name.',
        auth: 'Bearer token',
        permission: 'managetags on auth',
        requiresSignIn: true,
        noFieldsText: 'No parameters. Send it as is.',
        more: 'Which tags exist is up to you. Register them here, then assign them to roles with Save role metadata. Like other auth:* permissions, auth:managetags is granted by anyone with roleupdate on a role, and the root admin always has it.',
        fields: [],
        buildRequest: () => ({}),
    },
    {
        id: 'create-role-tag',
        group: 'Role tags',
        method: 'POST',
        path: '/role-tags',
        title: 'Create a tag',
        description: 'Registers a tag so it can be assigned to roles.',
        auth: 'Bearer token',
        permission: 'managetags on auth',
        requiresSignIn: true,
        more: 'Names are unique, ignoring case, and can’t be changed later. A duplicate comes back as 409.',
        fields: [
            tagNameField('Feature'),
            { name: 'description', label: 'Description', multiline: true, placeholder: 'Roles that act as feature flags', hint: 'Optional.' },
        ],
        buildRequest: (values) => ({
            body: { name: values.name ?? '', description: filledText(values.description) ?? null },
        }),
    },
    {
        id: 'update-role-tag',
        group: 'Role tags',
        method: 'PATCH',
        path: '/role-tags/{name}',
        title: 'Update a tag',
        description: 'Changes a tag’s description.',
        auth: 'Bearer token',
        permission: 'managetags on auth',
        requiresSignIn: true,
        more: 'Only the description can change. Roles that have the tag keep it.',
        fields: [
            tagNameField('Feature'),
            { name: 'description', label: 'Description', multiline: true, placeholder: 'Roles that act as feature flags', hint: 'Leave blank to clear the description.' },
        ],
        buildRequest: (values) => ({
            path: tagPath(values),
            body: { description: filledText(values.description) ?? null },
        }),
    },
    {
        id: 'delete-role-tag',
        group: 'Role tags',
        method: 'DELETE',
        path: '/role-tags/{name}',
        title: 'Delete a tag',
        description: 'Removes a tag from the registry.',
        auth: 'Bearer token',
        permission: 'managetags on auth',
        requiresSignIn: true,
        more: 'Returns 204 with no body. A tag can’t be deleted while any role still has it; the 409 response lists those roles.',
        fields: [tagNameField('Feature')],
        buildRequest: (values) => ({ path: tagPath(values) }),
    },
];

/** Sends only the fields that were filled in or checked to clear, since a missing field keeps its value. */
function buildSaveMetadataBody(values) {
    const fieldsToClear = values.clear ?? [];
    const tags = parseLines(values.tags);
    const sentValues = {
        alias: filledText(values.alias),
        tags: tags.length ? tags : undefined,
        description: filledText(values.description),
    };

    const body = { role: values.role ?? '' };
    for (const [field, value] of Object.entries(sentValues)) {
        if (fieldsToClear.includes(field)) {
            body[field] = null;
        } else if (value !== undefined) {
            body[field] = value;
        }
    }
    return body;
}
