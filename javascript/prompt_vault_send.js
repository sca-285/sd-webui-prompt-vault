// Prompt Vault: its icon on its tab, and a button under the txt2img and img2img galleries that
// takes the image shown there to the Vault tab's Image → Prompt.

(() => {
    'use strict';

    const ICON = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" aria-hidden="true">'
        + '<defs><linearGradient id="pv-icon-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffb43a"/>'
        + '<stop offset="1" stop-color="#ea580c"/></linearGradient></defs>'
        + '<rect x="2" y="2" width="60" height="60" rx="14" fill="url(#pv-icon-bg)"/>'
        + '<rect x="9" y="14" width="42" height="42" rx="9" fill="none" stroke="#fff" stroke-width="4"/>'
        + '<rect x="6" y="21" width="5" height="7" rx="2" fill="#fff"/><rect x="6" y="42" width="5" height="7" rx="2" fill="#fff"/>'
        + '<circle cx="30" cy="35" r="11" fill="none" stroke="#fff" stroke-width="3"/>'
        + '<g stroke="#fff" stroke-width="3" stroke-linecap="round"><line x1="30" y1="35" x2="30" y2="21"/>'
        + '<line x1="30" y1="35" x2="42.1" y2="42"/><line x1="30" y1="35" x2="17.9" y2="42"/></g>'
        + '<g fill="#fff"><circle cx="30" cy="21" r="2.6"/><circle cx="42.1" cy="42" r="2.6"/><circle cx="17.9" cy="42" r="2.6"/>'
        + '<circle cx="30" cy="35" r="4"/></g>'
        + '<path d="M51 3 L53.4 9.6 L60 12 L53.4 14.4 L51 21 L48.6 14.4 L42 12 L48.6 9.6 Z" fill="#fff" stroke="#ea580c" '
        + 'stroke-width="1.5" stroke-linejoin="round"/></svg>';

    const app = () => (typeof gradioApp === 'function' ? gradioApp() : document);
    const $ = (sel, root) => (root || app()).querySelector(sel);
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));

    function icon(cls) {
        const span = document.createElement('span');
        span.className = cls;
        span.innerHTML = ICON;
        return span;
    }

    function toast(message, bad) {
        const box = $('#pv_toast') || (document.querySelector('.gradio-container') || document.body).appendChild(Object.assign(document.createElement('div'), {id: 'pv_toast'}));
        box.textContent = message;
        box.className = 'pv-show' + (bad ? ' pv-bad' : '');
        clearTimeout(toast.t);
        toast.t = setTimeout(() => { box.className = ''; }, bad ? 5000 : 2200);
    }

    function vaultTabButton() {
        return [...app().querySelectorAll('#tabs > .tab-nav button, #tabs > div > button')]
            .find((b) => b.textContent.trim().replace(/\s+/g, ' ').endsWith('Prompt Vault'));
    }

    // the icon in front of the tab's name: style.css draws it where the button says which tab it is
    // (Gradio 4); older WebUIs get it here, again whenever the tab bar is redrawn
    function tabIcon() {
        const b = vaultTabButton();
        if (!b || b.getAttribute('aria-controls')) return;
        if (!b.querySelector('.pv-tab-icon')) b.prepend(icon('pv-tab-icon'));
        if (!tabIcon.watching && b.parentElement) {
            tabIcon.watching = true;
            new MutationObserver(() => { const x = vaultTabButton(); if (x && !x.querySelector('.pv-tab-icon')) x.prepend(icon('pv-tab-icon')); })
                .observe(b.parentElement, {childList: true, subtree: true});
        }
    }

    // the image the gallery shows: the one picked, or the first
    function shownImage(tab) {
        const gallery = $(`#${tab}_gallery`);
        if (!gallery) return '';
        const thumbs = [...gallery.querySelectorAll('.thumbnail-item img, .thumbnails img')];
        let i = -1;
        try { if (typeof selected_gallery_index === 'function') i = selected_gallery_index(); } catch (e) { /* not that gallery */ }
        if (thumbs[i]) return thumbs[i].src;
        const preview = gallery.querySelector('.preview img, button.image-button img, img');
        return (preview && preview.src) || (thumbs[0] && thumbs[0].src) || '';
    }

    async function sendToVault(tab) {
        const src = shownImage(tab);
        if (!src) { toast('No image in ' + tab + ' yet', true); return; }
        let file;
        try {
            const blob = await (await fetch(src)).blob();
            file = new File([blob], 'image.png', {type: blob.type || 'image/png'});
        } catch (e) { toast('Could not read the image: ' + e.message, true); return; }
        const tabButton = vaultTabButton();
        if (!tabButton) { toast('The Prompt Vault tab is not on the page', true); return; }
        tabButton.click();
        await wait(150);
        const acc = $('#pv_image');
        const head = acc && acc.querySelector('.label-wrap');
        if (head && !head.classList.contains('open')) { head.click(); await wait(250); }
        const clear = $('#pv_image_input button[aria-label="Clear"], #pv_image_input button[title="Clear"]');
        if (clear) { clear.click(); await wait(250); }
        const input = $('#pv_image_input input[type="file"]');
        if (!input) { toast('Image → Prompt is not ready: open it once and try again', true); return; }
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        input.dispatchEvent(new Event('change', {bubbles: true}));
        acc.scrollIntoView({behavior: 'smooth', block: 'start'});
        toast('In Image → Prompt: read it, or use the prompt saved in it');
    }

    // next to the WebUI's own "send to" buttons, the same kind of button
    function sendButtons() {
        for (const tab of ['txt2img', 'img2img']) {
            const row = $(`#image_buttons_${tab}`);
            if (!row || $(`#${tab}_send_to_prompt_vault`)) continue;
            const like = $(`#${tab}_send_to_extras`) || row.querySelector('button');
            const b = document.createElement('button');
            b.id = `${tab}_send_to_prompt_vault`;
            b.type = 'button';
            b.className = (like ? like.className : 'lg secondary tool') + ' pv-send-vault';
            b.title = 'Send the image to Prompt Vault: Image → Prompt';
            b.setAttribute('aria-label', b.title);
            b.append(icon('pv-send-icon'));
            b.addEventListener('click', () => sendToVault(tab));
            (like && like.parentElement === row ? like : row.lastElementChild).after(b);
        }
    }

    const boot = () => {
        tabIcon();
        sendButtons();
        if (!vaultTabButton() || !$('#image_buttons_txt2img')) setTimeout(boot, 800);
    };
    if (typeof onUiLoaded === 'function') onUiLoaded(boot);
    else document.addEventListener('DOMContentLoaded', () => setTimeout(boot, 1000));
})();
