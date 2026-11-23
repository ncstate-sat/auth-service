/** Field definitions shared by more than one endpoint module. */

export const roleField = (placeholder, hint = '') => ({ name: 'role', label: 'Role', placeholder, hint });

/** The text of a field, or undefined when it was left blank. */
export function filledText(text) {
    const trimmed = String(text ?? '').trim();
    return trimmed || undefined;
}
