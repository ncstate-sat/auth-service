const API_BASE = 'http://localhost:8000';

const STATUS_LABELS = {
    pending: 'Pending',
    active: 'In progress',
    complete: 'Complete',
    error: 'Error',
};

function announce(message) {
    document.getElementById('status-announcer').textContent = message;
}

function setStepStatus(stepNumber, status, errorMessage) {
    const step = document.getElementById(`step-${stepNumber}`);
    const badge = step.querySelector(`[data-status-for="${stepNumber}"]`);
    const errorEl = document.getElementById(`error-${stepNumber}`);

    step.classList.remove('stepper__step--pending', 'stepper__step--active', 'stepper__step--complete', 'stepper__step--error');
    step.classList.add(`stepper__step--${status}`);

    badge.classList.remove('status-badge--pending', 'status-badge--active', 'status-badge--complete', 'status-badge--error');
    badge.classList.add(`status-badge--${status}`);
    badge.textContent = STATUS_LABELS[status];

    if (status === 'error' && errorMessage) {
        errorEl.textContent = errorMessage;
        errorEl.hidden = false;
    } else {
        errorEl.hidden = true;
    }

    const title = step.querySelector('.stepper__title').textContent.trim();
    announce(`${title}: ${STATUS_LABELS[status]}`);
}

function base64UrlDecode(segment) {
    let base64 = segment.replace(/-/g, '+').replace(/_/g, '/');
    const paddingNeeded = base64.length % 4;
    if (paddingNeeded) {
        base64 += '='.repeat(4 - paddingNeeded);
    }
    return atob(base64);
}

function decodeJwt(token) {
    const parts = token.split('.');
    if (parts.length < 2) {
        return null;
    }
    try {
        return {
            header: JSON.parse(base64UrlDecode(parts[0])),
            payload: JSON.parse(base64UrlDecode(parts[1])),
        };
    } catch (error) {
        return null;
    }
}

function renderJwt(prefix, token) {
    document.getElementById(`raw-${prefix}`).textContent = token;

    const decoded = decodeJwt(token);
    const details = document.getElementById(`details-${prefix}`);
    if (decoded) {
        document.getElementById(`decoded-${prefix}-header`).textContent = JSON.stringify(decoded.header, null, 2);
        document.getElementById(`decoded-${prefix}-payload`).textContent = JSON.stringify(decoded.payload, null, 2);
        details.hidden = false;
    } else {
        details.hidden = true;
    }
}

function renderJson(elementId, value) {
    document.getElementById(elementId).textContent = JSON.stringify(value, null, 2);
}

async function handleCredentialResponse(response) {
    setStepStatus(1, 'active');
    renderJwt('credential', response.credential);
    setStepStatus(1, 'complete');

    setStepStatus(2, 'active');
    let signInResult;
    try {
        const signInResponse = await fetch(`${API_BASE}/google-sign-in`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ token: response.credential }),
        });
        if (!signInResponse.ok) {
            throw new Error(`Request failed with status ${signInResponse.status}`);
        }
        signInResult = await signInResponse.json();
    } catch (error) {
        setStepStatus(2, 'error', `Could not reach ${API_BASE}/google-sign-in: ${error.message}`);
        return;
    }

    renderJwt('token', signInResult.token);
    renderJwt('refresh-token', signInResult.refresh_token);
    setStepStatus(2, 'complete');

    setStepStatus(3, 'active');
    try {
        const loginResponse = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${signInResult.token}`,
            },
            body: JSON.stringify({ token: signInResult.token }),
        });
        if (!loginResponse.ok) {
            throw new Error(`Request failed with status ${loginResponse.status}`);
        }
        const loginResult = await loginResponse.json();
        renderJson('raw-payload', loginResult);
        setStepStatus(3, 'complete');
    } catch (error) {
        setStepStatus(3, 'error', `Could not reach ${API_BASE}/login: ${error.message}`);
    }
}

document.addEventListener('click', (event) => {
    const button = event.target.closest('.copy-btn');
    if (!button) {
        return;
    }
    const target = document.getElementById(button.dataset.copyTarget);
    if (!target || !target.textContent) {
        return;
    }
    navigator.clipboard.writeText(target.textContent).then(() => {
        const originalLabel = button.textContent;
        button.textContent = 'Copied!';
        setTimeout(() => {
            button.textContent = originalLabel;
        }, 1500);
    });
});

window.onload = function () {
    google.accounts.id.initialize({
        client_id: '4944492663-6msau4peegvm3oqa9pbgsmncorfkj5sa.apps.googleusercontent.com',
        callback: handleCredentialResponse,
    });
    google.accounts.id.renderButton(
        document.getElementById('buttonDiv'),
        { theme: 'outline', size: 'large' }
    );
};
