/**
 * Ticks the auth token's time remaining into every countdown element.
 * The value isn't in a live region; screen readers only hear the
 * five-minute, one-minute, and expired thresholds.
 */

import { announce } from './dom.js';

const THRESHOLD_ANNOUNCEMENTS = [
    { secondsLeft: 0, message: 'Auth token expired. Use Refresh token to get a new one.' },
    { secondsLeft: 60, message: 'Auth token expires in under a minute.' },
    { secondsLeft: 300, message: 'Auth token expires in under five minutes.' },
];

let timer = null;
let expiresAtSeconds = null;
let announcedThresholds = new Set();

export function startCountdown(expiresAt) {
    stopCountdown();
    expiresAtSeconds = expiresAt ?? null;
    announcedThresholds = new Set();
    tick();
    timer = setInterval(tick, 1000);
}

export function stopCountdown() {
    clearInterval(timer);
    timer = null;
}

function tick() {
    if (!expiresAtSeconds) {
        renderCountdown('Token expiry', 'not in token', false);
        stopCountdown();
        return;
    }
    const secondsLeft = Math.floor(expiresAtSeconds - Date.now() / 1000);
    announceCrossedThreshold(secondsLeft);
    if (secondsLeft <= 0) {
        renderCountdown('Auth token', 'expired', true);
        stopCountdown();
        return;
    }
    renderCountdown('Token expires in', formatMinutesSeconds(secondsLeft), secondsLeft <= 60);
}

function renderCountdown(label, value, isWarning) {
    document.getElementById('countdown-label').textContent = label;
    for (const valueElement of [document.getElementById('countdown-value'), document.getElementById('session-countdown')]) {
        valueElement.textContent = value;
        valueElement.classList.toggle('countdown-value--warning', isWarning);
    }
}

function announceCrossedThreshold(secondsLeft) {
    const crossed = THRESHOLD_ANNOUNCEMENTS.find((threshold) => secondsLeft <= threshold.secondsLeft);
    if (crossed && !announcedThresholds.has(crossed.secondsLeft)) {
        markThresholdAndAllAbove(crossed.secondsLeft);
        announce(crossed.message);
    }
}

function markThresholdAndAllAbove(secondsLeft) {
    for (const threshold of THRESHOLD_ANNOUNCEMENTS) {
        if (threshold.secondsLeft >= secondsLeft) {
            announcedThresholds.add(threshold.secondsLeft);
        }
    }
}

function formatMinutesSeconds(totalSeconds) {
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${String(seconds).padStart(2, '0')}`;
}
