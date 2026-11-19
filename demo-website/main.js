/* ────────────────────────── CONFIGURE ME ──────────────────────────
   Set this to your Google OAuth client ID — the same value as the
   GOOGLE_CLIENT_ID environment variable described in the README.
   (The service's own URL lives at the top of api.js as API_BASE.)
   ─────────────────────────────────────────────────────────────────── */
const GOOGLE_CLIENT_ID = '4944492663-6msau4peegvm3oqa9pbgsmncorfkj5sa.apps.googleusercontent.com';

import { onRecord } from './api.js';
import { initWire, recordWireEntry } from './wire.js';
import { onSessionChange } from './session.js';
import { initTopBar } from './top-bar.js';
import { initSidebar } from './sidebar.js';
import { initSessionPage } from './session-page.js';
import { initEndpointPage } from './endpoint-page.js';
import { initPageSwitcher } from './page-switcher.js';
import { initRouter } from './router.js';
import { initGoogleSignIn, resetSignInFlow } from './google-sign-in.js';
import { prefillSessionEmail } from './request-form.js';
import { clearResponses } from './response-store.js';
import { ENDPOINTS } from './endpoints.js';

onRecord(recordWireEntry);
onSessionChange(prepareWorkbenchForSession);
initWire();
initTopBar();
initSidebar();
initSessionPage();
initEndpointPage();
initPageSwitcher();
initRouter();
initGoogleSignIn(GOOGLE_CLIENT_ID);

function prepareWorkbenchForSession(session) {
    if (session) {
        prefillSessionEmail(ENDPOINTS, session.payload.email ?? '');
        return;
    }
    clearResponses();
    resetSignInFlow();
}
