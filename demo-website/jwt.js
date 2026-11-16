/** Decodes a JWT into { header, payload }, or null if it isn't one. Signatures aren't checked. */
export function decodeJwt(token) {
    const parts = (token ?? '').split('.');
    if (parts.length < 2) {
        return null;
    }
    try {
        return {
            header: JSON.parse(decodeBase64Url(parts[0])),
            payload: JSON.parse(decodeBase64Url(parts[1])),
        };
    } catch (error) {
        return null;
    }
}

function decodeBase64Url(segment) {
    let base64 = segment.replace(/-/g, '+').replace(/_/g, '/');
    const paddingNeeded = base64.length % 4;
    if (paddingNeeded) {
        base64 += '='.repeat(4 - paddingNeeded);
    }
    return atob(base64);
}
