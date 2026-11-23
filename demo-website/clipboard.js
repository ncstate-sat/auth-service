import { announce } from './dom.js';

const CONFIRMATION_MS = 1600;

/** Copies text and briefly relabels the button "Copied". */
export async function copyWithConfirmation(button, text) {
    try {
        await navigator.clipboard.writeText(text);
    } catch (error) {
        announce('Copying failed. Your browser blocked clipboard access.');
        return;
    }
    const originalLabel = button.dataset.originalLabel ?? button.textContent;
    button.dataset.originalLabel = originalLabel;
    button.textContent = 'Copied';
    announce('Copied to clipboard.');
    clearTimeout(button.copyConfirmationTimer);
    button.copyConfirmationTimer = setTimeout(() => {
        button.textContent = originalLabel;
    }, CONFIRMATION_MS);
}
