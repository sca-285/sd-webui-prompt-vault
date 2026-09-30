// Prompt Vault Muse: a floating button on every tab that offers prompt ideas, now and then or on demand.
// The ideas come from lib_vault/muse.py (packs in data/muse_packs); this file only shows them.

(() => {
    'use strict';

    const API = '/prompt-vault/api';
    const KEEP = 20; // ideas kept for ‹ ›
    const LS = {
        get(key, fallback) { try { const v = localStorage.getItem('pv_muse_' + key); return v === null ? fallback : JSON.parse(v); } catch (e) { return fallback; } },
        set(key, value) { try { localStorage.setItem('pv_muse_' + key, JSON.stringify(value)); } catch (e) { /* private window */ } },
    };

    const app = () => (typeof gradioApp === 'function' ? gradioApp() : document);
    // inside the Gradio container, the panel takes the theme's font and colours
    const layer = () => document.querySelector('.gradio-container') || document.body;
    const $ = (sel, root) => (root || document).querySelector(sel);
    const el = (tag, attrs, ...children) => {
        const node = document.createElement(tag);
        for (const [k, v] of Object.entries(attrs || {})) {
            if (v === undefined || v === null || v === false) continue;
            if (k === 'class') node.className = v;
            else if (k === 'text') node.textContent = v;
            else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
            else node.setAttribute(k, v === true ? '' : v);
        }
        for (const c of children.flat()) if (c !== null && c !== undefined && c !== false) node.append(c);
        return node;
    };

    // stroke icons, not emoji: Lobe Theme swaps the label of any button holding certain emoji
    const PATHS = {
        spark: 'M9 18h6M10 21h4M12 3a6 6 0 0 0-3.6 10.8c.7.6 1.1 1.3 1.1 2.2h5c0-.9.4-1.6 1.1-2.2A6 6 0 0 0 12 3z',
        gear: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z',
        close: 'M6 6l12 12M18 6L6 18',
        pause: 'M9 5v14M15 5v14',
        play: 'M7 4l13 8-13 8z',
        prev: 'M15 5l-7 7 7 7',
        next: 'M9 5l7 7-7 7',
        back: 'M19 12H5M11 5l-7 7 7 7',
        copy: 'M9 9h11v11H9zM5 15V4h11',
    };
    function icon(name) {
        const ns = 'http://www.w3.org/2000/svg';
        const svg = document.createElementNS(ns, 'svg');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('aria-hidden', 'true');
        svg.setAttribute('class', 'pv-muse-icon');
        const path = document.createElementNS(ns, 'path');
        path.setAttribute('d', PATHS[name]);
        svg.append(path);
        return svg;
    }
    const iconButton = (name, title, onclick, extra) => el('button', Object.assign({type: 'button', class: 'pv-muse-icon-btn', title, 'aria-label': title, onclick}, extra || {}), icon(name));

    function root() { return ((window.gradio_config && window.gradio_config.root) || '').replace(/\/$/, ''); }

    async function call(path, body) {
        const opts = body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)};
        const res = await fetch(root() + API + path, opts);
        let data = null;
        try { data = await res.json(); } catch (e) { /* not json */ }
        if (!res.ok) throw new Error((data && data.error) || ('HTTP ' + res.status));
        return data;
    }

    function toast(message, bad) {
        // the same toast as the Vault tab
        const box = $('#pv_toast', app()) || $('#pv_toast') || layer().appendChild(el('div', {id: 'pv_toast'}));
        box.textContent = message;
        box.className = 'pv-show' + (bad ? ' pv-bad' : '');
        clearTimeout(toast.t);
        toast.t = setTimeout(() => { box.className = ''; }, bad ? 5000 : 2200);
    }

    // ------------------------------------------------------------------ state

    const M = {
        snap: null,                         // {state, packs, avatar}
        ideas: LS.get('ideas', []),
        at: -1,
        open: false,
        view: 'idea',                       // or 'settings'
        busy: '',                           // '', 'next' or 'tipo'
        due: LS.get('due', 0),              // when the timer brings the next idea (ms)
        fresh: false,                       // an idea came while the panel was closed
        dragged: false,
    };
    M.at = M.ideas.length - 1;

    const st = () => (M.snap && M.snap.state) || {};
    const idea = () => M.ideas[M.at] || null;
    const intervalMs = () => Math.max(5, Math.min(30, +st().interval_minutes || 15)) * 60000;
    const timed = () => !!M.snap && st().enabled && !st().paused;

    function setDue(t) { M.due = t; LS.set('due', t); }
    function saveIdeas() { LS.set('ideas', M.ideas.slice(-KEEP)); }

    // ------------------------------------------------------------------ the WebUI's prompt boxes

    const TARGETS = {txt2img: ['txt2img_prompt', 'txt2img_neg_prompt'], img2img: ['img2img_prompt', 'img2img_neg_prompt'], vault: ['pv_positive', 'pv_negative']};
    const TARGET_NAMES = {txt2img: 'txt2img', img2img: 'img2img', vault: 'the Vault editor'};

    const area = (id) => app().querySelector('#' + id + ' textarea');

    function write(box, value) {
        box.value = value;
        if (typeof updateInput === 'function') updateInput(box);
        else box.dispatchEvent(new Event('input', {bubbles: true}));
    }

    function pieces(prompt) {
        const pv = window.promptVault;
        if (pv && pv.split) return pv.split(prompt);
        return String(prompt || '').split(/[,\n]/).map((p) => p.trim()).filter(Boolean);
    }
    const keyOf = (p) => (window.promptVault && window.promptVault.key ? window.promptVault.key(p) : p.trim().toLowerCase());

    // what is missing from current, added at the end; nothing already there is touched
    function addMissing(current, addition) {
        const have = new Set(pieces(current).map(keyOf));
        const extra = pieces(addition).filter((p) => !have.has(keyOf(p)));
        if (!extra.length) return current;
        const base = current.replace(/[\s,]+$/, '');
        return base ? base + ', ' + extra.join(', ') : extra.join(', ');
    }

    function generating() {
        for (const id of ['txt2img_interrupt', 'img2img_interrupt']) {
            const n = app().querySelector('#' + id);
            if (n && n.offsetParent !== null && getComputedStyle(n).visibility !== 'hidden') return true;
        }
        return false;
    }

    function send() {
        const it = idea();
        if (!it) return;
        const s = st();
        const target = TARGETS[s.target] ? s.target : 'txt2img';
        const [posId, negId] = TARGETS[target];
        const pos = area(posId);
        if (!pos) { toast('The ' + TARGET_NAMES[target] + ' prompt box is not on the page', true); return; }
        write(pos, s.send_mode === 'append' && pos.value.trim() ? addMissing(pos.value, it.positive) : it.positive);
        const neg = s.send_negative && it.negative ? area(negId) : null;
        if (neg) write(neg, addMissing(neg.value, it.negative));
        const go = window['switch_to_' + target];
        if (typeof go === 'function') { try { go(); } catch (e) { /* the tab switch is a nicety */ } }
        toast('Sent to ' + TARGET_NAMES[target] + (neg ? ', negatives added' : ''));
    }

    // ------------------------------------------------------------------ ideas

    async function nextIdea(quiet) {
        if (M.busy) return;
        M.busy = 'next';
        render();
        try {
            const data = await call('/muse/next', {});
            M.ideas.push(data.idea);
            if (M.ideas.length > KEEP) M.ideas.splice(0, M.ideas.length - KEEP);
            M.at = M.ideas.length - 1;
            saveIdeas();
            if (quiet) M.fresh = true;
            else if (timed()) setDue(Date.now() + intervalMs());
        } catch (e) {
            if (!quiet) toast(e.message, true);
        } finally {
            M.busy = '';
            render();
            paintFab();
        }
    }

    async function expandTipo() {
        const it = idea();
        if (!it || M.busy) return;
        M.busy = 'tipo';
        render();
        try {
            const data = await call('/muse/tipo', {positive: it.positive});
            it.positive = data.positive;
            it.note = data.note;
            saveIdeas();
        } catch (e) {
            toast(e.message, true);
        } finally {
            M.busy = '';
            render();
        }
    }

    // ------------------------------------------------------------------ panel

    function openPanel(yes) {
        M.open = yes;
        const panel = $('#pv_muse_panel');
        if (!panel) return;
        panel.hidden = !yes;
        if (yes) {
            M.fresh = false;
            if (!idea() && M.snap) nextIdea(false);
            render();
        }
        paintFab();
    }

    function place() {
        const fab = $('#pv_muse_fab'), panel = $('#pv_muse_panel');
        if (!fab || !panel || panel.hidden) return;
        const r = fab.getBoundingClientRect();
        const w = panel.offsetWidth, h = panel.offsetHeight, gap = 10, pad = 8;
        let left = r.left + r.width / 2 > innerWidth / 2 ? r.right - w : r.left;
        left = Math.max(pad, Math.min(innerWidth - w - pad, left));
        let top = r.top + r.height / 2 > innerHeight / 2 ? r.top - h - gap : r.bottom + gap;
        top = Math.max(pad, Math.min(innerHeight - h - pad, top));
        panel.style.left = left + 'px';
        panel.style.top = top + 'px';
    }

    function statusText() {
        const s = st();
        if (!M.snap) return '';
        if (!s.enabled) return 'Timer off';
        if (s.paused) return 'Paused';
        const min = Math.max(0, Math.ceil((M.due - Date.now()) / 60000));
        return min <= 1 ? 'Next idea soon' : `Next idea in ${min} min`;
    }

    function avatarNode(cls) {
        const url = M.snap && M.snap.avatar && M.snap.avatar.url;
        return url ? el('img', {class: cls, src: root() + API + url, alt: '', draggable: 'false'}) : el('span', {class: cls + ' pv-muse-noface'}, icon('spark'));
    }

    function header() {
        const s = st();
        const title = M.view === 'settings'
            ? el('div', {class: 'pv-muse-title'}, iconButton('back', 'Back to the idea', () => { M.view = 'idea'; render(); }), el('strong', {text: 'Muse settings'}))
            : el('div', {class: 'pv-muse-title'}, avatarNode('pv-muse-face-sm'),
                el('div', {class: 'pv-muse-title-text'}, el('strong', {text: 'Muse'}), el('span', {class: 'pv-muse-status', id: 'pv_muse_status', text: statusText()})));
        return el('div', {class: 'pv-muse-head'}, title,
            s.enabled ? iconButton(s.paused ? 'play' : 'pause', s.paused ? 'Resume the timer' : 'Pause the timer', () => patch({paused: !s.paused})) : null,
            M.view === 'idea' ? iconButton('gear', 'Settings', () => { M.view = 'settings'; render(); }) : null,
            iconButton('close', 'Close (Esc)', () => openPanel(false)));
    }

    function ideaView() {
        const it = idea();
        if (!it) {
            return el('div', {class: 'pv-muse-body pv-muse-empty'},
                el('p', {text: M.busy ? 'Thinking…' : 'No idea yet.'}),
                el('button', {type: 'button', class: 'pv-btn pv-primary', text: 'Give me one', disabled: !!M.busy, onclick: () => nextIdea(false)}));
        }
        const s = st();
        const prompt = el('textarea', {class: 'pv-muse-text', rows: '5', spellcheck: 'false', 'aria-label': 'Positive prompt'});
        prompt.value = it.positive;
        prompt.addEventListener('input', () => { it.positive = prompt.value; clearTimeout(ideaView.t); ideaView.t = setTimeout(saveIdeas, 400); });
        const nav = M.ideas.length > 1 ? el('div', {class: 'pv-muse-nav'},
            iconButton('prev', 'Previous idea', () => { M.at--; render(); }, {disabled: M.at <= 0}),
            el('span', {text: `${M.at + 1}/${M.ideas.length}`}),
            iconButton('next', 'Next idea', () => { M.at++; render(); }, {disabled: M.at >= M.ideas.length - 1})) : null;

        return el('div', {class: 'pv-muse-body'},
            el('div', {class: 'pv-muse-meta'},
                el('span', {class: 'pv-muse-pill' + (it.nsfw ? ' pv-muse-nsfw' : ''), text: it.pack_name}), nav),
            it.spark ? el('div', {class: 'pv-muse-spark', text: it.spark}) : null,
            it.twist ? el('div', {class: 'pv-muse-twist', text: it.twist}) : null,
            prompt,
            it.negative ? el('details', {class: 'pv-muse-neg'},
                el('summary', {text: s.send_negative ? 'Negatives, added on send' : 'Negatives, not sent'}),
                el('div', {text: it.negative})) : null,
            it.note ? el('div', {class: 'pv-muse-note', text: it.note}) : null,
            el('div', {class: 'pv-muse-actions'},
                el('button', {type: 'button', class: 'pv-btn pv-primary pv-muse-send', text: 'Send to ' + (s.target === 'vault' ? 'Vault' : s.target || 'txt2img'), onclick: send}),
                el('button', {type: 'button', class: 'pv-btn', text: M.busy === 'next' ? 'Thinking…' : 'Another', disabled: !!M.busy, onclick: () => nextIdea(false)}),
                s.use_tipo ? el('button', {type: 'button', class: 'pv-btn', text: M.busy === 'tipo' ? 'TIPO…' : 'TIPO', title: 'Expand with TIPO (settings: Prompt Vault (TIPO))', disabled: !!M.busy, onclick: expandTipo}) : null,
                iconButton('copy', 'Copy the prompt', () => {
                    navigator.clipboard.writeText(prompt.value).then(() => toast('Copied'), () => toast('The clipboard is blocked here', true));
                })));
    }

    // ------------------------------------------------------------------ settings

    async function patch(body) {
        try {
            const before = st();
            const data = await call('/muse/state', body);
            M.snap.state = data.state;
            const s = data.state;
            if (s.interval_minutes !== before.interval_minutes || (s.enabled && !s.paused && (!before.enabled || before.paused))) setDue(Date.now() + intervalMs());
        } catch (e) {
            toast(e.message, true);
        }
        render();
        paintFab();
    }

    function toggle(label, on, change, hint) {
        return el('button', {type: 'button', class: 'pv-muse-switch', role: 'switch', 'aria-checked': on ? 'true' : 'false', onclick: () => change(!on)},
            el('span', {class: 'pv-muse-track'}),
            el('span', {class: 'pv-muse-switch-text'}, el('span', {text: label}), hint ? el('small', {text: hint}) : null));
    }

    function seg(label, key, options) {
        const value = st()[key];
        return el('div', {class: 'pv-muse-field'},
            el('span', {class: 'pv-muse-field-label', text: label}),
            el('div', {class: 'pv-muse-seg', role: 'radiogroup'}, options.map(([v, text]) => el('button', {
                type: 'button', role: 'radio', 'aria-checked': v === value ? 'true' : 'false',
                class: v === value ? 'pv-on' : '', text, onclick: () => { if (v !== value) patch({[key]: v}); },
            }))));
    }

    function section(title, ...children) {
        return el('section', {class: 'pv-muse-section'}, el('h4', {text: title}), ...children);
    }

    function packChips(list, chosen) {
        return el('div', {class: 'pv-muse-chips'}, list.map((p) => {
            const on = chosen.has(p.id);
            return el('button', {
                type: 'button', class: 'pv-muse-chip' + (on ? ' pv-on' : '') + (p.nsfw ? ' pv-muse-nsfw' : ''),
                'aria-pressed': on ? 'true' : 'false', title: `${p.size} entries${p.custom ? ', your own pack' : ''}`, text: p.name,
                onclick: () => {
                    const next = new Set(chosen);
                    if (on) next.delete(p.id); else next.add(p.id);
                    const visible = (M.snap.packs || []).filter((x) => st().allow_nsfw || !x.nsfw);
                    if (!visible.some((x) => next.has(x.id))) { toast('Keep at least one pack on', true); return; }
                    patch({packs: [...next]});
                },
            });
        }));
    }

    function settingsView() {
        const s = st();
        const packs = M.snap.packs || [];
        const chosen = new Set(s.packs || packs.filter((p) => !p.nsfw).map((p) => p.id));

        const range = el('input', {type: 'range', min: '5', max: '30', step: '1', value: String(s.interval_minutes), 'aria-label': 'Minutes between ideas', disabled: !s.enabled});
        const rangeText = el('output', {text: s.interval_minutes + ' min'});
        range.addEventListener('input', () => { rangeText.textContent = range.value + ' min'; });
        range.addEventListener('change', () => patch({interval_minutes: +range.value}));

        const blacklist = el('textarea', {class: 'pv-muse-text', rows: '2', spellcheck: 'false', placeholder: 'e.g. hat, rain, red hair'});
        blacklist.value = s.blacklist || '';
        blacklist.addEventListener('change', () => patch({blacklist: blacklist.value}));

        const file = el('input', {type: 'file', accept: 'image/png,image/webp,image/jpeg,image/gif', hidden: true, onchange: onAvatar});
        const sfw = packs.filter((p) => !p.nsfw), nsfw = packs.filter((p) => p.nsfw);

        return el('div', {class: 'pv-muse-body pv-muse-settings'},
            section('Timer',
                toggle('Bring ideas by themselves', s.enabled, (v) => patch({enabled: v}), 'never while an image is generating'),
                el('div', {class: 'pv-muse-field' + (s.enabled ? '' : ' pv-muse-off')}, el('span', {class: 'pv-muse-field-label', text: 'Every'}), range, rangeText)),
            section('Packs',
                packChips(sfw, chosen),
                toggle('NSFW packs', s.allow_nsfw, (v) => {
                    // turning NSFW off with only NSFW packs chosen falls back to every SFW pack
                    const sfwLeft = sfw.some((p) => chosen.has(p.id));
                    patch(v || sfwLeft ? {allow_nsfw: v} : {allow_nsfw: v, packs: null});
                }, 'adults only; minors are always kept out'),
                s.allow_nsfw && nsfw.length ? packChips(nsfw, chosen) : null,
                el('div', {class: 'pv-muse-hint', text: 'Packs of your own: JSON files in prompt_vault/muse/packs.'})),
            section('Send',
                seg('To', 'target', [['txt2img', 'txt2img'], ['img2img', 'img2img'], ['vault', 'Vault']]),
                seg('How', 'send_mode', [['replace', 'Replace'], ['append', 'Append']]),
                toggle('Add the idea\'s negatives too', s.send_negative, (v) => patch({send_negative: v}), 'only the ones missing from the negative prompt')),
            section('TIPO',
                toggle('Show the TIPO button', s.use_tipo, (v) => patch({use_tipo: v}), 'expands an idea with the TIPO set up in the Vault tab'),
                s.use_tipo ? seg('Output', 'tipo_output', [['Tags', 'Tags'], ['Natural language', 'Words'], ['Tags + natural language', 'Both']]) : null,
                s.use_tipo ? seg('Length', 'tipo_length', [['very short', 'XS'], ['short', 'S'], ['long', 'L'], ['very long', 'XL']]) : null),
            section('Never use', blacklist,
                el('div', {class: 'pv-muse-hint', text: 'Comma-separated. Whole words only; they also go to the negatives.'})),
            section('Avatar',
                el('div', {class: 'pv-muse-avatar-row'}, avatarNode('pv-muse-face-lg'),
                    el('button', {type: 'button', class: 'pv-btn', text: 'Choose an image…', onclick: () => file.click()}), file,
                    M.snap.avatar.url ? el('button', {type: 'button', class: 'pv-btn', text: 'Remove', onclick: () => setAvatar(call('/muse/avatar/clear', {}))}) : null)));
    }

    function onAvatar(ev) {
        const f = ev.target.files && ev.target.files[0];
        ev.target.value = '';
        if (!f) return;
        if (f.size > 4 * 1024 * 1024) { toast('The avatar must be under 4 MB', true); return; }
        const reader = new FileReader();
        reader.onload = () => setAvatar(call('/muse/avatar', {data: reader.result}), 'Avatar saved');
        reader.readAsDataURL(f);
    }

    function setAvatar(promise, done) {
        promise.then((data) => {
            M.snap.avatar = data.avatar;
            render();
            paintFab();
            if (done) toast(done);
        }).catch((e) => toast(e.message, true));
    }

    // ------------------------------------------------------------------ drawing

    function render() {
        const panel = $('#pv_muse_panel');
        if (!panel || !M.open || !M.snap) return;
        const scroll = panel.querySelector('.pv-muse-body');
        const y = scroll ? scroll.scrollTop : 0;
        panel.replaceChildren(header(), M.view === 'settings' ? settingsView() : ideaView());
        const again = panel.querySelector('.pv-muse-body');
        if (again) again.scrollTop = y;
        place();
    }

    function paintFab() {
        const fab = $('#pv_muse_fab');
        if (!fab) return;
        const face = fab.querySelector('.pv-muse-fab-face');
        const url = (M.snap && M.snap.avatar && M.snap.avatar.url) || '';
        if (face.dataset.url !== url) {
            face.dataset.url = url;
            face.replaceChildren(avatarNode('pv-muse-face-fill'));
        }
        fab.classList.toggle('pv-muse-fresh', M.fresh && !M.open);
        fab.classList.toggle('pv-muse-open', M.open);
        fab.classList.toggle('pv-muse-idle', !timed());
        // the ring fills up towards the next idea
        const ring = fab.querySelector('.pv-muse-ring-fill');
        const left = timed() ? Math.max(0, Math.min(1, (M.due - Date.now()) / intervalMs())) : 1;
        ring.style.strokeDashoffset = String(100 * left);
        fab.title = 'Muse: ' + (statusText() || 'ideas') + ' · Alt+M: an idea now';
        const status = $('#pv_muse_status');
        if (status) status.textContent = statusText();
    }

    function tick() {
        if (!timed()) { paintFab(); return; }
        const now = Date.now();
        if (!M.due || M.due - now > intervalMs()) setDue(now + intervalMs());
        // an idea waits for a quiet moment: the panel closed, nothing generating, the page seen
        if (now >= M.due && !M.open && !M.busy && !generating() && !document.hidden) {
            setDue(now + intervalMs());
            nextIdea(true);
        }
        paintFab();
    }

    function mount() {
        const ns = 'http://www.w3.org/2000/svg';
        const ring = document.createElementNS(ns, 'svg');
        ring.setAttribute('class', 'pv-muse-ring');
        ring.setAttribute('viewBox', '0 0 36 36');
        ring.setAttribute('aria-hidden', 'true');
        for (const cls of ['pv-muse-ring-track', 'pv-muse-ring-fill']) {
            const c = document.createElementNS(ns, 'circle');
            c.setAttribute('cx', '18'); c.setAttribute('cy', '18'); c.setAttribute('r', '16.5');
            c.setAttribute('pathLength', '100');
            c.setAttribute('class', cls);
            ring.append(c);
        }
        const fab = el('button', {id: 'pv_muse_fab', type: 'button', 'aria-label': 'Muse', 'aria-haspopup': 'dialog',
            onclick: () => { if (M.dragged) { M.dragged = false; return; } openPanel(!M.open); }},
        ring, el('span', {class: 'pv-muse-fab-face'}), el('span', {class: 'pv-muse-dot'}));
        const panel = el('div', {id: 'pv_muse_panel', role: 'dialog', 'aria-label': 'Muse', hidden: true});
        panel.addEventListener('keydown', (ev) => { if (ev.key === 'Escape') { openPanel(false); fab.focus(); } });
        layer().append(fab, panel);
        dragging(fab);
        paintFab();
    }

    function putFab(fab, x, y) {
        const size = fab.offsetWidth || 52, pad = 8;
        x = Math.max(pad, Math.min(innerWidth - size - pad, x));
        y = Math.max(pad, Math.min(innerHeight - size - pad, y));
        fab.style.left = x + 'px';
        fab.style.top = y + 'px';
        return {x, y};
    }

    function dragging(fab) {
        // kept as the distance from the right and bottom edges: the button stays in its corner on resize
        const restore = () => {
            const p = LS.get('pos', {right: 20, bottom: 20});
            const size = fab.offsetWidth || 52;
            putFab(fab, innerWidth - size - p.right, innerHeight - size - p.bottom);
            place();
        };
        restore();
        addEventListener('resize', restore);
        fab.addEventListener('pointerdown', (ev) => {
            if (ev.button !== 0) return;
            const r = fab.getBoundingClientRect(), sx = ev.clientX, sy = ev.clientY;
            let moved = false;
            fab.setPointerCapture(ev.pointerId);
            const move = (e) => {
                if (!moved && Math.hypot(e.clientX - sx, e.clientY - sy) < 5) return;
                moved = true;
                fab.classList.add('pv-muse-dragging');
                putFab(fab, r.left + e.clientX - sx, r.top + e.clientY - sy);
                place();
            };
            const up = () => {
                fab.removeEventListener('pointermove', move);
                fab.removeEventListener('pointerup', up);
                fab.removeEventListener('pointercancel', up);
                fab.classList.remove('pv-muse-dragging');
                if (!moved) return;
                M.dragged = true; // the click that follows a drag does not open the panel
                setTimeout(() => { M.dragged = false; }, 0);
                const b = fab.getBoundingClientRect();
                LS.set('pos', {right: Math.round(innerWidth - b.right), bottom: Math.round(innerHeight - b.bottom)});
            };
            fab.addEventListener('pointermove', move);
            fab.addEventListener('pointerup', up);
            fab.addEventListener('pointercancel', up);
        });
    }

    // ------------------------------------------------------------------ start

    async function boot() {
        if (window.opts && opts.pv_muse === false) return;
        if ($('#pv_muse_fab')) return;
        try {
            M.snap = await call('/muse');
        } catch (e) {
            console.warn('[Prompt Vault] Muse:', e.message);
            return;
        }
        mount();
        // after a reload the timer starts over rather than firing at once
        if (timed() && (!M.due || M.due < Date.now())) setDue(Date.now() + intervalMs());
        setInterval(tick, 5000);
        tick();
        document.addEventListener('keydown', (ev) => {
            if (!ev.altKey || ev.ctrlKey || ev.metaKey || ev.code !== 'KeyM') return;
            ev.preventDefault();
            if (!M.open) openPanel(true);
            M.view = 'idea';
            nextIdea(false);
        });
        document.addEventListener('pointerdown', (ev) => {
            // a click anywhere else closes the panel, unless it was a click into a prompt box
            if (!M.open || ev.target.closest('#pv_muse_panel, #pv_muse_fab, .pv-shade, #pv_toast')) return;
            if (ev.target.closest('textarea, input')) return;
            openPanel(false);
        }, true);
    }

    if (typeof onUiLoaded === 'function') onUiLoaded(boot);
    else document.addEventListener('DOMContentLoaded', () => setTimeout(boot, 1200));
})();
