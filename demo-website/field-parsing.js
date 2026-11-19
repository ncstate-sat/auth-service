/** Turns what people type into request fields into the shapes the API expects. */

export function parseLines(text) {
    return String(text ?? '')
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean);
}

/** Parses "object:action" lines into { obj, act } pairs. */
export function parsePermissionLines(text) {
    return parseLines(text).map((line) => {
        const separatorIndex = line.indexOf(':');
        if (separatorIndex === -1) {
            return { obj: line, act: '' };
        }
        return { obj: line.slice(0, separatorIndex).trim(), act: line.slice(separatorIndex + 1).trim() };
    });
}
