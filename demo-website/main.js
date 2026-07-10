/* ────────────────────────── CONFIGURE ME ──────────────────────────
   Set this to your Google OAuth client ID — the same value as the
   GOOGLE_CLIENT_ID environment variable described in the README.
   (The service's own URL lives at the top of api.js as API_BASE.)
   ─────────────────────────────────────────────────────────────────── */
const GOOGLE_CLIENT_ID = '4944492663-6msau4peegvm3oqa9pbgsmncorfkj5sa.apps.googleusercontent.com';

import { initCopyButtons } from './ui.js';
import { onRecord } from './api.js';
import { initWire, recordEntry } from './wire.js';
import { initSession, onSessionChange } from './session.js';
import { handleCredential, resetHandshake, reportSignInUnavailable } from './handshake.js';
import { initRoles, loadRoles, resetRoles } from './roles.js';
import { initAccounts, resetAccounts, prefillEmail } from './accounts.js';

initCopyButtons();
initWire();
onRecord(recordEntry);
initSession();
initRoles();
initAccounts();

let signedIn = false;

onSessionChange((isSignedIn, email) => {
    if (isSignedIn === signedIn) {
        // A token refresh, not a transition — leave the workbench alone.
        return;
    }
    signedIn = isSignedIn;

    const workbench = document.getElementById('workbench');
    const panels = document.getElementById('workbench-panels');
    workbench.classList.toggle('workbench--locked', !isSignedIn);
    workbench.classList.toggle('workbench--unlocked', isSignedIn);
    panels.inert = !isSignedIn;

    if (isSignedIn) {
        prefillEmail(email);
        loadRoles();
    } else {
        resetHandshake();
        resetRoles();
        resetAccounts();
    }
});

/* The GSI script is loaded async, so it may not be ready the moment
   this module runs — poll briefly before declaring it unavailable. */

const GSI_RETRY_MS = 300;
const GSI_TIMEOUT_MS = 6000;
let gsiWaited = 0;

function initGoogleSignIn() {
    if (typeof google === 'undefined' || !google.accounts) {
        gsiWaited += GSI_RETRY_MS;
        if (gsiWaited >= GSI_TIMEOUT_MS) {
            reportSignInUnavailable(
                'Google Identity Services did not load. Check your network connection, then reload the page.',
            );
            return;
        }
        setTimeout(initGoogleSignIn, GSI_RETRY_MS);
        return;
    }

    google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleCredential,
    });
    google.accounts.id.renderButton(
        document.getElementById('google-button'),
        { theme: 'outline', size: 'large' },
    );
}

initGoogleSignIn();
