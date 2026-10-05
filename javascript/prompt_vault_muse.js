// Prompt Vault Muse: a floating button on every tab that gives prompt ideas, on demand or on a timer.
// Ideas come from lib_vault/muse.py (scenes in data/muse_scenes); this file shows them and lets
// you filter them, roll or lock each part, and send them to a prompt box.

(() => {
    'use strict';

    const API = '/prompt-vault/api';
    const KEEP = 500; // ideas kept for ‹ ›
    const LS = {
        get(key, fallback) { try { const v = localStorage.getItem('pv_muse_' + key); return v === null ? fallback : JSON.parse(v); } catch (e) { return fallback; } },
        set(key, value) { try { localStorage.setItem('pv_muse_' + key, JSON.stringify(value)); return true; } catch (e) { return false; /* private window, or full */ } },
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
        idea: 'M9 18h6M10 21h4M12 3a6 6 0 0 0-3.6 10.8c.7.6 1.1 1.3 1.1 2.2h5c0-.9.4-1.6 1.1-2.2A6 6 0 0 0 12 3z',
        gear: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z',
        close: 'M6 6l12 12M18 6L6 18',
        clock: 'M12 7v5l3 2M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z',
        prev: 'M15 5l-7 7 7 7',
        next: 'M9 5l7 7-7 7',
        back: 'M19 12H5M11 5l-7 7 7 7',
        copy: 'M9 9h11v11H9zM5 15V4h11',
        save: 'M6 3h10l4 4v14H6zM9 3v5h6V3M9 21v-7h8v7',
        trash: 'M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3',
        widen: 'M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7',
        narrow: 'M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7',
        roll: 'M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7',
        lock: 'M7 11V8a5 5 0 0 1 10 0v3M5 11h14v10H5z',
        unlock: 'M7 11V8a5 5 0 0 1 9.6-2M5 11h14v10H5z',
        down: 'M6 9l6 6 6-6',
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
        snap: null,                         // {state, catalogue, avatar}
        ideas: LS.get('ideas', []).filter((i) => i && Array.isArray(i.parts)),
        at: -1,
        open: false,
        view: 'idea',                       // or 'settings'
        tray: '',                           // the open filter: '', 'themes', 'casts' or 'ratings'
        busy: '',                           // '', 'next', 'tipo' or the slot being rolled
        due: LS.get('due', 0),
        pane: LS.get('pane', 'ideas'),      // ideas | chat              // when the timer brings the next idea (ms)
        fresh: false,                       // an idea came while the panel was closed
        dragged: false,
        wide: LS.get('wide', false),        // the wide card: two columns
    };
    const WIDE_MIN = 760; // narrower windows get the compact card
    const isWide = () => M.wide && innerWidth >= WIDE_MIN;
    M.at = M.ideas.length - 1;

    const st = () => (M.snap && M.snap.state) || {};
    const idea = () => M.ideas[M.at] || null;
    const intervalMs = () => Math.max(5, Math.min(30, +st().interval_minutes || 15)) * 60000;
    const timed = () => !!M.snap && !!st().enabled;

    function setDue(t) { M.due = t; LS.set('due', t); }
    function saveIdeas() {
        // the browser's storage is a few MB: when it is full, the oldest ideas give way
        for (const n of [KEEP, 200, 50]) if (LS.set('ideas', M.ideas.slice(-n))) return;
    }

    const PART_NAMES = {subject: 'Who', job: 'Job', outfit: 'Wear', build: 'Build', skin: 'Skin', body: 'Body', hair: 'Hair', eyes: 'Eyes',
        face: 'Features', makeup: 'Makeup', accessory: 'Accessory', pet: 'Animal', expression: 'Expression', mouth: 'Mouth', gaze: 'Gaze',
        gesture: 'Pose', action: 'Doing', kink: 'Kink', fx: 'FX', detail: 'Detail', setting: 'Where', time: 'When', lighting: 'Source',
        natural: 'Natural', light_quality: 'Quality', light_mood: 'Mood', light_support: 'Support', light_volume: 'Volume', camera: 'Shot',
        angle: 'Angle', view: 'View', framing: 'Framing', color: 'Color', style: 'Style'};
    // the long names, for tooltips
    const PART_TITLES = {face: 'Eyebrows, nose, lips', natural: 'Natural light', light_quality: 'Light quality', light_mood: 'Mood lighting',
        light_support: 'Support light', light_volume: 'Volume light', lighting: 'Light source', camera: 'Shot size', view: 'Viewpoint',
        color: 'Color & grading', pet: 'An animal with them', fx: 'Effects'};
    // the parts in groups on the card
    const PART_GROUPS = [['Character', ['subject', 'job', 'outfit', 'pet', 'build', 'skin', 'body']],
        ['Face', ['hair', 'eyes', 'face', 'makeup', 'accessory', 'expression', 'mouth', 'gaze']],
        ['Action', ['gesture', 'action', 'kink', 'fx']], ['Scene', ['detail', 'setting', 'time']],
        ['Light', ['lighting', 'natural', 'light_quality', 'light_mood', 'light_support', 'light_volume']],
        ['Camera', ['camera', 'angle', 'view', 'framing']], ['Look', ['color', 'style']]];
    const GROUP_OF = Object.fromEntries(PART_GROUPS.flatMap(([g, slots]) => slots.map((x) => [x, g])));
    // the parts, a block per group: filled ones as rows, empty ones as small chips that draw them.
    // A group turned off in the settings is not there at all.
    function partRows(it) {
        const byGroup = new Map();
        for (const p of it.parts) {
            const g = GROUP_OF[p.slot] || 'Other';
            if (!byGroup.has(g)) byGroup.set(g, []);
            byGroup.get(g).push(p);
        }
        return [...byGroup].map(([g, parts]) => {
            const filled = parts.filter((p) => p.value), empty = parts.filter((p) => !p.value);
            return el('div', {class: 'pv-muse-group'},
                el('div', {class: 'pv-muse-group-head'}, el('span', {class: 'pv-muse-group-name', text: g})),
                filled.map((p) => partRow(it, p)),
                empty.length ? el('div', {class: 'pv-muse-adds'}, empty.map((p) => {
                    // a click draws it; a double-click writes it yourself (the click waits to tell them apart)
                    const chip = el('button', {type: 'button', class: 'pv-muse-add', disabled: !!M.busy,
                        title: 'Draw ' + (PART_TITLES[p.slot] || PART_NAMES[p.slot] || p.slot).toLowerCase() + ' · double-click: write your own',
                        onclick: () => { clearTimeout(chip.t); chip.t = setTimeout(() => rollPart(p.slot), 250); },
                        ondblclick: () => { clearTimeout(chip.t); editPart(it, p.slot, chip); }}, '+ ' + (PART_NAMES[p.slot] || p.slot));
                    return chip;
                })) : null);
        });
    }
    const RATING_NSFW = (r) => r !== 'sfw';

    // ------------------------------------------------------------------ filters

    function ratingsOn(s) { return (s.ratings || []).filter((r) => r === 'sfw' || s.allow_nsfw); }

    // how many scenes match, with one of the three filters replaced by `over`
    function countMatching(over) {
        const cat = M.snap.catalogue, s = st();
        const themes = new Set(over && over.themes || s.themes || []);
        const casts = new Set(over && over.casts || s.casts || []);
        const ratings = new Set(over && over.ratings || ratingsOn(s));
        const sizes = new Set(over && over.sizes || s.sizes || []);
        const kinks = new Set(over && over.kinks || s.kinks || []);
        const acts = new Set(s.allow_nsfw ? (over && over.acts || s.acts || []) : []);
        const actCasts = cat.act_casts || {}, kinkActs = cat.kink_acts || {};
        // with an act chosen, only explicit scenes, and casts that have such an act (and a kink to go with it)
        const castActs = (c, k) => !acts.size || [...acts].some((a) => (actCasts[a] || []).includes(c) && (!k || ((kinkActs[k] || {})[a] || []).includes(c)));
        const kinkThemes = Object.fromEntries((cat.kinks || []).map(([k, , t]) => [k, t]));
        const groups = cat.group_sizes || {};
        // with a kink chosen, a scene counts when it is NSFW and of a theme one of the kinks belongs to
        const kinky = (theme, r) => !kinks.size || (r !== 'sfw' && s.allow_nsfw && [...kinks].some((k) => !kinkThemes[k] || kinkThemes[k].includes(theme)));
        // and a cast counts when one of those kinks has something for it (breeding needs a penis and a pussy)
        const kinkCasts = cat.kink_casts || {};
        const castKinky = (c, theme, r) => !kinks.size ? castActs(c) : [...kinks].some((k) => (!kinkThemes[k] || kinkThemes[k].includes(theme))
            && ((kinkCasts[k] || {})[r] || []).includes(c) && castActs(c, k));
        // a group cast counts only with a size the scene, the cast and the size filter all allow
        const usable = (c, scSizes) => !groups[c] || scSizes.some((n) => groups[c].includes(n) && (!sizes.size || sizes.has(n)));
        let n = 0;
        // a row stands for every scene alike in theme, casts, level and group sizes: [theme, cast set, level, size set, how many]
        for (const [ti, ci, r, si, many] of cat.index) {
            const sc = cat.castsets[ci], scSizes = cat.sizesets[si];
            if (!ratings.has(r) || (acts.size && r !== 'explicit')) continue;
            if (themes.size && !themes.has(cat.themes[ti])) continue;
            if (!kinky(cat.themes[ti], r)) continue;
            if (!sc.some((c) => (!casts.size || casts.has(c)) && usable(c, scSizes || []) && castKinky(c, cat.themes[ti], r))) continue;
            n += many;
        }
        return n;
    }

    function summary(key) {
        const s = st(), cat = M.snap.catalogue;
        if (key === 'themes') return s.themes.length ? (s.themes.length === 1 ? s.themes[0] : s.themes.length + ' themes') : 'All themes';
        if (key === 'casts') {
            if (!s.casts.length) return 'Anyone';
            const names = Object.fromEntries(cat.casts);
            return s.casts.length <= 2 ? s.casts.map((c) => names[c] || c).join(', ') : s.casts.length + ' casts';
        }
        if (key === 'styles') {
            if (!s.styles.length) return "Scene's own";
            return s.styles.length <= 2 ? s.styles.join(', ') : s.styles.length + ' families';
        }
        if (key === 'acts') {
            if (!s.acts.length) return 'Any';
            const names = Object.fromEntries(cat.acts);
            return s.acts.length <= 2 ? s.acts.map((a) => names[a]).join(', ') : s.acts.length + ' acts';
        }
        if (key === 'kinks') {
            if (!s.kinks.length) return 'None';
            const names = Object.fromEntries(cat.kinks.map(([k, l]) => [k, l]));
            return s.kinks.length <= 2 ? s.kinks.map((k) => names[k]).join(', ') : s.kinks.length + ' kinks';
        }
        const on = ratingsOn(s);
        const names = Object.fromEntries(cat.ratings);
        return on.length ? (on.length <= 2 ? on.map((r) => names[r]).join(', ') : on.length + ' levels') : 'No level';
    }

    function filterBar() {
        const pill = (key, label) => el('button', {
            type: 'button', class: 'pv-muse-filter' + (M.tray === key ? ' pv-on' : ''), 'aria-expanded': M.tray === key ? 'true' : 'false',
            title: label, onclick: () => { M.tray = M.tray === key ? '' : key; render(); },
        }, el('span', {class: 'pv-muse-filter-label', text: label}), el('span', {class: 'pv-muse-filter-value', text: summary(key)}), icon('down'));
        const n = countMatching();
        // the scene first; then, once NSFW is on, a tier of its own for what happens in it
        return el('div', {class: 'pv-muse-filters'},
            el('div', {class: 'pv-muse-filter-row'}, pill('themes', 'Theme'), pill('casts', 'Cast'), pill('ratings', 'Level'), st().hide.includes('style') ? null : pill('styles', 'Style')),
            st().allow_nsfw ? el('div', {class: 'pv-muse-filter-row pv-muse-filter-row2'}, pill('acts', 'Act'), pill('kinks', 'Kink')) : null,
            M.tray ? tray(M.tray) : null,
            M.tray ? el('div', {class: 'pv-muse-hint', text: n ? `${n} scene${n === 1 ? '' : 's'} match` : 'Nothing matches: loosen a filter'}) : null);
    }

    function tray(key) {
        const s = st(), cat = M.snap.catalogue;
        const chosen = new Set(key === 'ratings' ? s.ratings : s[key]);
        if (key === 'styles') return styleTray();
        const options = key === 'themes' ? cat.themes.map((t) => [t, t]) : key === 'kinks' ? cat.kinks.map(([k, l]) => [k, l]) : key === 'acts' ? cat.acts : cat[key];
        const toggle = (value) => {
            const next = new Set(chosen);
            if (next.has(value)) next.delete(value); else next.add(value);
            patch({[key]: [...next]});
        };
        const chips = options.map(([value, label]) => {
            const nsfwLocked = key === 'ratings' && RATING_NSFW(value) && !s.allow_nsfw;
            const n = nsfwLocked ? 0 : countMatching({[key]: [value]});
            const on = chosen.has(value) && !nsfwLocked;
            // nothing there: no "0" to click into, a reason instead (a chosen chip stays clickable, to unchoose it)
            const empty = !n && !on;
            return el('button', {
                type: 'button', class: 'pv-muse-chip' + (on ? ' pv-on' : '') + (key === 'ratings' && RATING_NSFW(value) ? ' pv-muse-nsfw' : ''),
                'aria-pressed': on ? 'true' : 'false', disabled: nsfwLocked || empty,
                title: nsfwLocked ? 'Turn NSFW on first' : (empty ? whyNone(key, value) : `${n} scene${n === 1 ? '' : 's'} with the other filters`),
                onclick: () => toggle(value),
            }, label, key !== 'ratings' && n ? el('small', {text: String(n)}) : null);
        });
        const all = key !== 'ratings' ? el('button', {type: 'button', class: 'pv-muse-chip' + (chosen.size ? '' : ' pv-on'),
            text: {themes: 'All', casts: 'Anyone', kinks: 'None', acts: 'Any'}[key], onclick: () => patch({[key]: []})}) : null;
        return el('div', {class: 'pv-muse-tray'},
            key === 'ratings' ? toggleSwitch('NSFW', s.allow_nsfw, (v) => patch({allow_nsfw: v})) : null,
            el('div', {class: 'pv-muse-chips'}, all, chips),
            key === 'casts' ? sizeRow() : null);
    }

    // style families: the groups of the library's Style & Medium category; they replace the scene's styles
    function styleTray() {
        const s = st(), cat = M.snap.catalogue;
        const chosen = new Set(s.styles);
        return el('div', {class: 'pv-muse-tray'},
            el('div', {class: 'pv-muse-chips'},
                el('button', {type: 'button', class: 'pv-muse-chip' + (chosen.size ? '' : ' pv-on'), text: "Scene's own",
                    title: 'Each scene keeps the styles written for it', onclick: () => patch({styles: []})}),
                (cat.styles || []).map(([family, n]) => {
                    const on = chosen.has(family);
                    return el('button', {type: 'button', class: 'pv-muse-chip' + (on ? ' pv-on' : ''), 'aria-pressed': on ? 'true' : 'false',
                        title: `${n} styles from your library`, onclick: () => {
                            const next = new Set(chosen); if (on) next.delete(family); else next.add(family);
                            patch({styles: [...next]});
                        }}, family, el('small', {text: String(n)}));
                })));
    }

    // why a chip leads nowhere, in words
    // the levels a theme has scenes at
    function themeLevels(name) {
        const cat = M.snap.catalogue;
        if (!themeLevels.memo || themeLevels.memo.cat !== cat) {
            const by = {};
            for (const [ti, , r] of cat.index) (by[cat.themes[ti]] = by[cat.themes[ti]] || new Set()).add(r);
            themeLevels.memo = {cat, by};
        }
        return themeLevels.memo.by[name] || new Set();
    }

    function whyNone(key, value) {
        const s = st();
        const on = ratingsOn(s);
        if (key === 'casts' && value === 'none' && !on.includes('sfw')) return 'No humans: SFW scenes only. Add SFW to Level.';
        if (key === 'casts' && value === 'animal' && !on.includes('sfw')) return 'Animals: SFW scenes only. Add SFW to Level.';
        if (key === 'ratings' && s.casts.length && s.casts.every((c) => c === 'animal' || c === 'none')) return 'Animals and no humans: SFW only.';
        if (key === 'ratings' && s.casts.length === 1 && s.casts[0] === 'none') return 'No humans: SFW scenes only.';
        if (key === 'sizes' && value === 3 && s.casts.length && s.casts.every((c) => c === 'mixed')) return 'A mixed group is 4 people or more.';
        const kinkThemes = Object.fromEntries((M.snap.catalogue.kinks || []).map(([k, l, t]) => [k, [l, t]]));
        if (key === 'kinks' && !on.some((r) => r !== 'sfw')) return 'Kinks are NSFW: add a NSFW level.';
        if (key === 'acts' && !on.includes('explicit')) return 'Acts are explicit: add Explicit to Level.';
        if (key === 'ratings' && value !== 'explicit' && s.acts.length) return 'An act makes an explicit idea. Set Act to Any.';
        if (key === 'acts' && s.kinks.length) return 'None of the chosen kinks goes with this act.';
        if (key === 'casts' && s.acts.length && !s.kinks.length) return 'No such act for this cast.';
        if (key === 'ratings' && value === 'sfw' && s.kinks.length) return 'Kinks are NSFW: an SFW idea carries none. Set Kink to None.';
        const futa = ['futa', 'futa_girl', 'futa_boy'];
        if (key === 'casts' && futa.includes(value) && !on.some((r) => r !== 'sfw')) return 'Futanari: NSFW only. Add a NSFW level.';
        if (key === 'ratings' && value === 'sfw' && s.casts.length && s.casts.every((c) => futa.includes(c))) return 'Futanari: NSFW only.';
        // themes with only some levels (Red light: NSFW only; School: SFW only)
        const levelName = (r) => (M.snap.catalogue.ratings.find((x) => x[0] === r) || [r, r])[1];
        const lv = themeLevels(value);
        if (key === 'themes' && !on.some((r) => lv.has(r))) return `${value}: ${[...lv].map(levelName).join(', ')} only. Add it to Level.`;
        const chosen = s.themes || [];
        const noneAt = (test) => chosen.length && chosen.every((t) => !test(themeLevels(t)));
        if (key === 'ratings' && noneAt((l) => l.has(value))) return `${chosen.join(', ')}: no ${levelName(value)} scenes.`;
        const nsfwSide = (l) => [...l].some((r) => r !== 'sfw');
        if ((key === 'kinks' || key === 'acts') && noneAt(nsfwSide)) return `${chosen.join(', ')}: SFW only.`;
        if (key === 'casts' && futa.includes(value) && noneAt(nsfwSide)) return `${chosen.join(', ')}: SFW only, and futanari is NSFW only.`;
        const sfwCasts = (cs) => cs.length && cs.every((c) => c === 'animal' || c === 'none');
        if (key === 'themes' && sfwCasts(s.casts) && !lv.has('sfw')) return `${value} has no SFW side: no animals or empty scenes there.`;
        if (key === 'themes' && s.casts.length && s.casts.every((c) => futa.includes(c)) && !nsfwSide(lv)) return `${value}: SFW only, and futanari is NSFW only.`;
        if (key === 'casts' && (value === 'animal' || value === 'none') && noneAt((l) => l.has('sfw'))) return `${chosen.join(', ')} has no SFW side: no animals or empty scenes there.`;
        if (key === 'casts' && s.kinks.length) return `${s.kinks.map((k) => kinkThemes[k][0]).join(', ')}: nothing for this cast.`;
        if (key === 'kinks' && s.casts.length) return 'Nothing for the chosen cast: loosen Cast.';
        if (key === 'kinks' && kinkThemes[value] && kinkThemes[value][1]) return `${kinkThemes[value][0]}: ${kinkThemes[value][1].join(', ')} only.`;
        if (key === 'themes' && s.kinks.length && s.kinks.every((k) => kinkThemes[k] && kinkThemes[k][1])) {
            const where = [...new Set(s.kinks.flatMap((k) => kinkThemes[k][1]))];
            return `${s.kinks.map((k) => kinkThemes[k][0]).join(', ')}: ${where.join(', ')} only.`;
        }
        if (s.kinks.length && key !== 'kinks') return 'Not with the chosen kinks: loosen them.';
        return 'Nothing with the other filters: loosen one of them.';
    }

    // how many people in a group: only for the 3+ casts
    function sizeRow() {
        const s = st(), cat = M.snap.catalogue;
        const chosen = new Set(s.sizes);
        return el('div', {class: 'pv-muse-size'},
            el('span', {class: 'pv-muse-field-label', text: 'Group of'}),
            el('div', {class: 'pv-muse-chips'},
                el('button', {type: 'button', class: 'pv-muse-chip' + (chosen.size ? '' : ' pv-on'), text: 'Any', onclick: () => patch({sizes: []})}),
                cat.sizes.map(([n, label]) => {
                    const on = chosen.has(n);
                    const count = countMatching({sizes: [n]});
                    return el('button', {type: 'button', class: 'pv-muse-chip' + (on ? ' pv-on' : ''), disabled: !count && !on,
                        'aria-pressed': on ? 'true' : 'false', title: count ? `${count} scenes for a group of ${label}` : whyNone('sizes', n),
                        onclick: () => { const next = new Set(chosen); if (on) next.delete(n); else next.add(n); patch({sizes: [...next]}); }}, label);
                })));
    }

    // ------------------------------------------------------------------ the WebUI's prompt boxes

    const TARGETS = {txt2img: 'txt2img_prompt', img2img: 'img2img_prompt', vault: 'pv_positive'};
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

    // your own words, kept across ideas, go in front of Muse's tags
    // your own prompt: in front of every idea as it is, or the tags an idea is built around
    const around = () => st().prompt_mode === 'around';
    const ownPrompt = () => String(st().fixed_prompt || '').replace(/[\s,]+$/, '').replace(/^[\s,]+/, '');
    function fullPrompt(it) {
        const tags = String(it.positive || '').replace(/^[\s,]+/, '');
        if (around()) return tags; // Muse put your tags in the idea itself
        const own = ownPrompt();
        return own && tags ? own + ', ' + tags : own || tags;
    }

    // the tags of the Vault's library and Danbooru under a box while you type in it
    function suggest(box, onAccept) {
        const pv = window.promptVault;
        if (!pv || !pv.attachSuggest) return;
        // the list goes next to the box: once the box is on the page
        const attach = (tries) => {
            if (box.isConnected && box.parentElement) pv.attachSuggest(box, onAccept);
            else if (tries) setTimeout(() => attach(tries - 1), 0);
        };
        attach(5);
    }

    function ownBar() {
        const mode = around() ? 'around' : 'front';
        const box = el('textarea', {class: 'pv-muse-text pv-muse-own', rows: '1', spellcheck: 'false', 'aria-label': 'Your prompt',
            placeholder: mode === 'around' ? 'e.g. 1girl, red hair, bikini, beach, sunset: Enter for an idea around them'
                : 'e.g. masterpiece, best quality, <lora:name:0.8>'});
        box.value = st().fixed_prompt || '';
        const save = () => call('/muse/state', {fixed_prompt: box.value}).catch((e) => toast(e.message, true));
        box.addEventListener('input', () => {
            if (M.snap && M.snap.state) M.snap.state.fixed_prompt = box.value;
            clearTimeout(ownBar.t);
            ownBar.t = setTimeout(save, 500);
        });
        box.addEventListener('keydown', async (e) => {
            if (e.key !== 'Enter' || e.shiftKey) return;
            e.preventDefault();
            clearTimeout(ownBar.t);
            await save();
            if (around()) nextIdea(false);
            else box.blur();
        });
        suggest(box);
        const pick = (v, label, title) => el('button', {type: 'button', role: 'radio', 'aria-checked': v === mode ? 'true' : 'false',
            class: v === mode ? 'pv-on' : '', text: label, title, onclick: async () => {
                if (v === mode) return;
                clearTimeout(ownBar.t);
                await call('/muse/state', {fixed_prompt: box.value}).catch(() => {});
                await patch({prompt_mode: v});
                if (v === 'around' && box.value.trim()) nextIdea(false);
            }});
        return el('div', {class: 'pv-muse-ownbar'},
            el('div', {class: 'pv-muse-ownhead'},
                el('span', {class: 'pv-muse-prompt-label', text: 'Your prompt'}),
                el('div', {class: 'pv-muse-seg pv-muse-ownseg', role: 'radiogroup', 'aria-label': 'What Muse does with it'},
                    pick('front', 'Keep in front', 'Sent in front of every idea, as it is; new ideas never touch it'),
                    pick('around', 'Build around', 'Muse reads your tags (red hair: Hair, beach: Where, sunset: When), '
                        + 'picks a scene that has them and draws the rest; what it cannot place stays in front'))),
            box);
    }

    function cleanPrompt(value) {
        const pv = window.promptVault;
        return pv && pv.dedupePrompt ? pv.dedupePrompt(value || '') : (value || '');
    }

    function send(target) {
        const it = idea();
        if (!it) return;
        const s = st();
        const pos = area(TARGETS[target]);
        if (!pos) { toast('The ' + TARGET_NAMES[target] + ' prompt box is not on the page', true); return; }
        write(pos, cleanPrompt(s.send_mode === 'append' && pos.value.trim() ? addMissing(pos.value, fullPrompt(it)) : fullPrompt(it)));
        const go = window['switch_to_' + target];
        if (typeof go === 'function') { try { go(); } catch (e) { /* the tab switch is a nicety */ } }
        toast('Sent to ' + TARGET_NAMES[target]);
    }

    // ------------------------------------------------------------------ generate, right from the card

    const genTab = () => (st().generate_in === 'img2img' ? 'img2img' : 'txt2img');
    const galleryImages = (tab) => [...app().querySelectorAll(`#${tab}_gallery img`)].map((n) => n.src).filter(Boolean);

    // the idea goes into the chosen tab (txt2img, or img2img with its own input image) and that tab's
    // Generate button is pressed: the WebUI's own model and settings
    function generateImage() {
        const it = idea();
        if (!it || M.gen) return;
        const tab = genTab();
        const pos = area(TARGETS[tab]);
        const go = app().querySelector(`#${tab}_generate`);
        if (!pos || !go) { toast(tab + ' is not on the page', true); return; }
        if (generating()) { toast('An image is being generated: wait for it', true); return; }
        const s = st();
        write(pos, cleanPrompt(s.send_mode === 'append' && pos.value.trim() ? addMissing(pos.value, fullPrompt(it)) : fullPrompt(it)));
        const before = new Set(galleryImages(tab));
        M.gen = {id: it.id, started: Date.now(), seen: false, tab};
        render();
        setTimeout(() => go.click(), 60);
        const tick = () => {
            if (!M.gen) return;
            const busy = generating();
            if (busy) M.gen.seen = true;
            const fresh = galleryImages(tab).filter((src) => !before.has(src));
            const timedOut = Date.now() - M.gen.started > 15 * 60 * 1000;
            if ((M.gen.seen && !busy && fresh.length) || (!busy && fresh.length && Date.now() - M.gen.started > 3000) || timedOut) {
                const target = M.ideas.find((x) => x.id === M.gen.id);
                if (target && fresh.length) { target.images = fresh.slice(0, 4); saveIdeas(); }
                M.gen = null;
                render();
                toast(fresh.length ? `Done: the image is on the card and in ${tab}`
                    : (tab === 'img2img' ? 'No image came back: does img2img have an input image?' : 'No image came back'), !fresh.length);
                return;
            }
            setTimeout(tick, 700);
        };
        setTimeout(tick, 1200);
    }

    function imagesView(it) {
        if (!it.images || !it.images.length) return null;
        return el('div', {class: 'pv-muse-images'}, it.images.map((src) =>
            el('a', {href: src, target: '_blank', rel: 'noopener', title: 'Open the image'}, el('img', {src, alt: 'Generated image', loading: 'lazy'}))));
    }

    // ------------------------------------------------------------------ ideas

    // the parts to keep: the locked ones, or all of them when one part is rolled
    function keepOf(it, all) {
        const keep = {};
        for (const p of it.parts) if (all || (it.locks && it.locks[p.slot])) keep[p.slot] = p.value;
        return keep;
    }
    const lockCount = (it) => (it && it.locks ? Object.values(it.locks).filter(Boolean).length : 0);

    async function nextIdea(quiet) {
        if (M.busy) return;
        const cur = idea();
        const locked = !quiet && lockCount(cur) && fits(cur);
        M.busy = 'next';
        render();
        try {
            const body = locked ? {scene: cur.scene, cast: cur.cast, size: cur.size, girls: cur.girls, keep: keepOf(cur)} : {};
            let data;
            try {
                data = await call('/muse/next', body);
            } catch (e) {
                if (!locked) throw e;
                data = await call('/muse/next', {}); // the scene is gone: a fresh idea, locks dropped
            }
            const it = data.idea;
            it.styles_from = st().styles.join('|');
            if (locked && it.scene === cur.scene) {
                it.locks = Object.assign({}, cur.locks);
                it.mine = Object.fromEntries(Object.entries(cur.mine || {}).filter(([k, v]) => v && cur.locks[k]));
            }
            M.ideas.push(it);
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

    async function refreshIdea() {
        const it = idea();
        if (!it || M.busy) return;
        try {
            const data = await call('/muse/next', {scene: it.scene, cast: it.cast, size: it.size, girls: it.girls, keep: keepOf(it, true)});
            M.ideas[M.at] = Object.assign(data.idea, {locks: it.locks, images: it.images, mine: it.mine, seen: it.seen});
            saveIdeas();
            render();
        } catch (e) { /* the scene may be gone: the next idea will do */ }
    }

    // the idea again with every part as it is: a new prompt from the parts, same scene
    async function recompose(it) {
        const data = await call('/muse/next', {scene: it.scene, cast: it.cast, size: it.size, girls: it.girls, keep: keepOf(it, true)});
        const fresh = Object.assign(data.idea, {locks: it.locks, images: it.images, mine: it.mine, seen: it.seen});
        const i = M.ideas.indexOf(it);
        if (i >= 0) M.ideas[i] = fresh;
        saveIdeas();
        return fresh;
    }

    // a part written by hand, right on the card: Enter or leaving the box keeps it (locked), Esc does not
    function editPart(it, slot, node) {
        if (M.busy || !node || !node.parentElement) return;
        const part = it.parts.find((x) => x.slot === slot);
        const holder = el('span', {class: 'pv-muse-part-edit'});
        const input = el('input', {type: 'text', class: 'pv-muse-text', spellcheck: 'false', value: part ? part.value : '',
            'aria-label': (PART_NAMES[slot] || slot) + ': your own', placeholder: 'tags, comma-separated'});
        holder.append(input);
        node.replaceWith(holder);
        let done = false;
        const finish = async (keep) => {
            if (done) return;
            done = true;
            const v = input.value.replace(/^[\s,]+|[\s,]+$/g, '');
            if (!keep || (part && v === part.value)) { render(); return; }
            if (part) part.value = v;
            else it.parts.push({slot, value: v, choices: 0});
            it.locks = Object.assign({}, it.locks, {[slot]: !!v});
            it.mine = Object.assign({}, it.mine, {[slot]: !!v});
            M.busy = slot;
            render();
            try { await recompose(it); } catch (e) { toast(e.message, true); }
            M.busy = '';
            render();
        };
        suggest(input);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') { e.preventDefault(); finish(true); }
            else if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); finish(false); }
        });
        input.addEventListener('blur', () => setTimeout(() => { if (!holder.contains(document.activeElement)) finish(true); }, 180));
        input.focus();
        input.select();
    }

    // a part you do not want: gone from this idea (its + chip draws or writes it again)
    async function removePart(it, slot) {
        if (M.busy) return;
        const part = it.parts.find((x) => x.slot === slot);
        if (!part || !part.value) return;
        part.value = '';
        it.locks = Object.assign({}, it.locks, {[slot]: false});
        it.mine = Object.assign({}, it.mine, {[slot]: false});
        M.busy = slot;
        render();
        try { await recompose(it); } catch (e) { toast(e.message, true); }
        M.busy = '';
        render();
    }

    async function rollPart(slot) {
        const it = idea();
        if (!it || M.busy) return;
        M.busy = slot;
        render();
        try {
            // what this part has already been: each roll brings one not seen yet, until there are none left
            const part = it.parts.find((x) => x.slot === slot);
            const seen = Object.assign({}, it.seen);
            seen[slot] = [...new Set([...(seen[slot] || []), part && part.value].filter(Boolean))].slice(-60);
            const data = await call('/muse/next', {scene: it.scene, cast: it.cast, size: it.size, girls: it.girls, keep: keepOf(it, true),
                roll: slot, avoid: seen[slot]});
            const mine = Object.assign({}, it.mine, {[slot]: false}); // rolled: Muse's again
            const fresh = Object.assign(data.idea, {locks: it.locks, mine, seen}); // a fresh prompt: any paragraph is gone
            M.ideas[M.at] = fresh;
            saveIdeas();
        } catch (e) {
            toast(e.message, true);
        } finally {
            M.busy = '';
            render();
        }
    }

    // into the Vault tab's Saved prompts, under the scene's name and the time
    function saveToVault() {
        const it = idea();
        if (!it) return;
        const when = new Date().toLocaleString(undefined, {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'});
        call('/prompts/save', {name: `${it.title} · ${when}`, positive: fullPrompt(it), negative: ''})
            .then(() => {
                toast('Saved in the Vault tab');
                if (window.promptVault && window.promptVault.reloadSaved) window.promptVault.reloadSaved();
            })
            .catch((e) => toast(e.message, true));
    }

    // every idea goes but the one on the card
    function clearHistory() {
        if (M.ideas.length < 2 || !confirm(`Clear the ${M.ideas.length - 1} older ideas? The one on the card stays.`)) return;
        const it = idea();
        M.ideas = it ? [it] : [];
        M.at = M.ideas.length - 1;
        saveIdeas();
        render();
        toast('History cleared');
    }

    function toggleLock(slot) {
        const it = idea();
        if (!it) return;
        it.locks = Object.assign({}, it.locks, {[slot]: !(it.locks && it.locks[slot])});
        saveIdeas();
        render();
    }

    // the same tools as the Vault tab: arrange the tags, Qwen's paragraph, TIPO
    const TOOL_NAMES = {arrange: 'Arranging…', describe: 'Writing…', tipo: 'TIPO…'};

    async function tool(kind) {
        const it = idea();
        if (!it || M.busy) return;
        const s = st();
        M.busy = kind;
        render();
        try {
            // a paragraph Qwen wrote earlier is not fed back in
            const base = it.described ? it.tags : it.positive;
            let result, note;
            if (kind === 'tipo') {
                const data = await call('/muse/tipo', {positive: base});
                result = data.positive; note = data.note;
            } else if (kind === 'arrange' && s.arrange_with !== 'qwen') {
                ({result, note} = await call('/prompt/arrange', {prompt: base, parts: it.parts}));
            } else {
                const task = kind === 'arrange' ? 'Arrange tags' : 'Tags → sentence';
                ({result, note} = await call('/prompt/qwen', {prompt: base, task}));
            }
            if (kind === 'describe') {
                it.tags = base;
                it.described = true;
                it.positive = s.describe_as === 'both' ? base.replace(/[\s,]+$/, '') + ', ' + result : result;
            } else {
                it.positive = it.described && s.describe_as === 'both' ? it.positive.replace(base, result) : result;
                if (it.described) it.tags = result;
            }
            it.note = note;
            it.edited = true;
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
        if (!M.snap) return '';
        if (!timed()) return 'On demand · Alt+M';
        const min = Math.max(0, Math.ceil((M.due - Date.now()) / 60000));
        return min <= 1 ? 'Next idea soon' : `Next idea in ${min} min`;
    }

    function avatarNode(cls) {
        const url = M.snap && M.snap.avatar && M.snap.avatar.url;
        return url ? el('img', {class: cls, src: root() + API + url, alt: '', draggable: 'false'}) : el('span', {class: cls + ' pv-muse-noface'}, icon('idea'));
    }

    // Ideas, or the chat with Qwen: the same conversation as the Qwen Chat window of the Vault tab
    function panes() {
        const pick = (v, label, title) => el('button', {type: 'button', role: 'tab', 'aria-selected': M.pane === v ? 'true' : 'false',
            class: 'pv-muse-pane' + (M.pane === v ? ' pv-on' : ''), text: label, title,
            onclick: () => { if (M.pane !== v) { M.pane = v; LS.set('pane', v); render(); } }});
        return el('div', {class: 'pv-muse-panes', role: 'tablist'},
            pick('ideas', 'Ideas', 'Prompt ideas from scenes'),
            pick('chat', 'Chat', 'Talk with Qwen: the same conversation as in the Vault tab'));
    }

    function chatView() {
        const host = el('div', {class: 'pv-muse-body pv-muse-chat'});
        if (window.pvChat) setTimeout(() => window.pvChat.mount(host, {compact: true}), 0);
        else host.append(el('div', {class: 'pv-muse-empty', text: 'Qwen Chat is not loaded: reload the page.'}));
        return host;
    }

    function header() {
        const s = st();
        const title = M.view === 'settings'
            ? el('div', {class: 'pv-muse-title'}, iconButton('back', 'Back to the idea', () => { M.view = 'idea'; render(); }), el('strong', {text: 'Muse settings'}))
            : el('div', {class: 'pv-muse-title'}, avatarNode('pv-muse-face-sm'),
                el('div', {class: 'pv-muse-title-text'}, el('strong', {text: 'Muse'}), el('span', {class: 'pv-muse-status', id: 'pv_muse_status', text: statusText()})));
        return el('div', {class: 'pv-muse-head'}, title,
            iconButton('clock', s.enabled ? `Timer on, every ${s.interval_minutes} min: turn off` : 'Timer off: turn on', () => patch({enabled: !s.enabled}),
                {class: 'pv-muse-icon-btn' + (s.enabled ? ' pv-on' : ''), 'aria-pressed': s.enabled ? 'true' : 'false'}),
            innerWidth >= WIDE_MIN ? iconButton(isWide() ? 'narrow' : 'widen', isWide() ? 'Compact card' : 'Wide card: two columns, a bigger prompt',
                () => { M.wide = !M.wide; LS.set('wide', M.wide); render(); }) : null,
            M.view === 'idea' ? iconButton('gear', 'Settings', () => { M.view = 'settings'; M.qwen = null; render(); }) : null,
            iconButton('close', 'Close (Esc)', () => openPanel(false)));
    }

    function partRow(it, p) {
        const locked = !!(it.locks && it.locks[p.slot]);
        const rolling = M.busy === p.slot;
        const mine = !!(it.mine && it.mine[p.slot]);
        const seeded = !mine && (it.seeded || []).includes(p.slot);
        const value = el('span', {class: 'pv-muse-part-value', title: (p.value || '') + '\nDouble-click to write your own',
            ondblclick: () => editPart(it, p.slot, value)},
            seeded ? el('span', {class: 'pv-muse-mark', text: '🌱', title: 'From your prompt'}) : null,
            mine ? el('span', {class: 'pv-muse-mark', text: '✎', title: 'Written by you'}) : null,
            p.value || '—');
        return el('div', {class: 'pv-muse-part' + (locked ? ' pv-muse-locked' : '') + (p.value ? '' : ' pv-muse-empty-part')},
            el('span', {class: 'pv-muse-part-name', text: PART_NAMES[p.slot] || p.slot, title: PART_TITLES[p.slot] || PART_NAMES[p.slot] || p.slot}),
            value,
            p.slot === 'subject' ? el('span') : iconButton('close', 'Remove it from this idea', () => removePart(it, p.slot),
                {disabled: !!M.busy, class: 'pv-muse-icon-btn pv-muse-remove'}),
            iconButton('roll', 'Another ' + (PART_NAMES[p.slot] || p.slot).toLowerCase(), () => rollPart(p.slot),
                {disabled: !!M.busy || locked || (p.choices < 2 && !!p.value), class: 'pv-muse-icon-btn' + (rolling ? ' pv-muse-spin' : '')}),
            iconButton(locked ? 'lock' : 'unlock', locked ? 'Unlock' : 'Lock: keep it for the next idea', () => toggleLock(p.slot),
                {class: 'pv-muse-icon-btn' + (locked ? ' pv-on' : ''), 'aria-pressed': locked ? 'true' : 'false', disabled: !p.value}));
    }

    function ideaView() {
        const it = idea();
        const s = st();
        if (!it) {
            return el('div', {class: 'pv-muse-body'}, filterBar(), ownBar(),
                el('div', {class: 'pv-muse-empty'},
                    el('p', {text: M.busy ? 'Thinking…' : 'No idea yet.'}),
                    el('button', {type: 'button', class: 'pv-btn pv-primary', text: 'Give me one', disabled: !!M.busy, onclick: () => nextIdea(false)})));
        }
        const prompt = el('textarea', {class: 'pv-muse-text', rows: '3', spellcheck: 'false', 'aria-label': 'Prompt'});
        prompt.value = it.positive;
        prompt.addEventListener('input', () => { it.positive = prompt.value; it.edited = true; clearTimeout(ideaView.t); ideaView.t = setTimeout(saveIdeas, 400); });
        suggest(prompt);
        const nav = M.ideas.length > 1 ? el('div', {class: 'pv-muse-nav'},
            iconButton('prev', 'Previous idea', () => { M.at--; render(); }, {disabled: M.at <= 0}),
            el('span', {text: `${M.at + 1}/${M.ideas.length}`}),
            iconButton('next', 'Next idea', () => { M.at++; render(); }, {disabled: M.at >= M.ideas.length - 1}),
            iconButton('trash', 'Clear the history', clearHistory)) : null;

        const card = el('div', {class: 'pv-muse-card'},
                el('div', {class: 'pv-muse-card-head'},
                    el('div', {class: 'pv-muse-card-title'},
                        el('strong', {text: it.title}),
                        el('div', {class: 'pv-muse-tags'},
                            el('span', {text: it.theme}), el('span', {text: it.cast_label}),
                            el('span', {class: it.nsfw ? 'pv-muse-nsfw' : '', text: (M.snap.catalogue.ratings.find((r) => r[0] === it.rating) || [0, it.rating])[1]}))),
                    nav),
                el('div', {class: 'pv-muse-parts'}, partRows(it)));
        const label = it.edited ? 'Prompt (edited: rolling a part rewrites it)' : 'Prompt';
        const note = it.note ? el('div', {class: 'pv-muse-hint', text: it.note}) : null;

        if (isWide()) {
            // the parts on the left, the whole prompt on the right, always open
            prompt.rows = 12;
            return el('div', {class: 'pv-muse-body'},
                filterBar(), ownBar(),
                el('div', {class: 'pv-muse-cols'},
                    card,
                    el('div', {class: 'pv-muse-prompt pv-muse-prompt-wide'},
                        el('div', {class: 'pv-muse-prompt-label', text: label}), prompt, note, imagesView(it))));
        }
        return el('div', {class: 'pv-muse-body'},
            filterBar(), ownBar(),
            card,
            el('details', {class: 'pv-muse-prompt', open: LS.get('prompt_open', true) ? true : null,
                ontoggle: (e) => LS.set('prompt_open', e.target.open)},
            el('summary', {text: label}), prompt, note), imagesView(it));
    }

    // always in view, under the scrolling part
    function ideaFooter() {
        const it = idea();
        const s = st();
        if (!it) return null;
        const locks = lockCount(it);
        return el('div', {class: 'pv-muse-foot'},
            el('div', {class: 'pv-muse-actions'},
                el('button', {type: 'button', class: 'pv-btn pv-muse-new', disabled: !!M.busy, onclick: () => nextIdea(false),
                    title: locks ? 'Same scene, the locked parts stay' : 'A new scene (Alt+M)'},
                icon('roll'), M.busy === 'next' ? 'Thinking…' : (locks ? `New, keep ${locks} locked` : 'New idea')),
                el('button', {type: 'button', class: 'pv-btn', text: M.busy === 'arrange' ? TOOL_NAMES.arrange : 'Arrange', disabled: !!M.busy, onclick: () => tool('arrange'),
                    title: s.arrange_with === 'qwen' ? 'Qwen puts the tags in order, merges duplicates, fixes spelling' : 'Puts the tags in order, from what your library knows of them (instant)'}),
                el('button', {type: 'button', class: 'pv-btn', text: M.busy === 'describe' ? TOOL_NAMES.describe : 'Describe', disabled: !!M.busy, onclick: () => tool('describe'),
                    title: s.describe_as === 'both' ? 'Qwen writes a paragraph from the tags and adds it after them' : 'Qwen turns the tags into a paragraph'}),
                s.use_tipo ? el('button', {type: 'button', class: 'pv-btn', text: M.busy === 'tipo' ? TOOL_NAMES.tipo : 'TIPO', title: 'Expand with TIPO', disabled: !!M.busy, onclick: () => tool('tipo')}) : null,
                iconButton('save', 'Save to the Vault\'s saved prompts', saveToVault),
                iconButton('copy', 'Copy the prompt', () => {
                    navigator.clipboard.writeText(fullPrompt(it)).then(() => toast('Copied'), () => toast('The clipboard is blocked here', true));
                })),
            el('div', {class: 'pv-muse-send'},
                el('button', {type: 'button', class: 'pv-btn pv-primary pv-muse-generate', disabled: !!M.gen,
                    title: `Writes the idea in ${genTab()} and presses its Generate button: your model, sampler, size and negative prompt `
                        + `as they are there; the image comes back here. Settings → Send picks txt2img or img2img.`,
                    text: M.gen ? `Generating in ${M.gen.tab}…` : `Generate in ${genTab()}`, onclick: generateImage}),
                el('div', {class: 'pv-muse-sendseg', role: 'group', 'aria-label': s.send_mode === 'append' ? 'Append to' : 'Send to',
                    title: s.send_mode === 'append' ? 'Append the idea to…' : 'Send the idea to…'},
                    el('span', {class: 'pv-muse-sendseg-label', text: s.send_mode === 'append' ? 'Append to' : 'Send to'}),
                    ['txt2img', 'img2img', 'vault'].map((t) => el('button', {type: 'button', class: 'pv-btn', text: t === 'vault' ? 'Vault' : t, onclick: () => send(t)})))));
    }

    // ------------------------------------------------------------------ settings

    function fits(it) {
        const s = st();
        return (!s.themes.length || s.themes.includes(it.theme)) && (!s.casts.length || s.casts.includes(it.cast))
            && ratingsOn(s).includes(it.rating) && (!it.size || !s.sizes.length || s.sizes.includes(it.size))
            && (!s.kinks.length || it.parts.some((p) => p.slot === 'kink' && p.value))
            && (!s.acts.length || !s.allow_nsfw || it.rating === 'explicit')
            && (!s.styles.length || it.styles_from === s.styles.join('|'));
    }

    async function patch(body) {
        try {
            const before = st();
            const data = await call('/muse/state', body);
            M.snap.state = data.state;
            const s = data.state;
            if (s.enabled && (!before.enabled || s.interval_minutes !== before.interval_minutes)) setDue(Date.now() + intervalMs());
        } catch (e) {
            toast(e.message, true);
        }
        render();
        paintFab();
        // a filter changed and the idea on the card no longer fits it: a fitting one, once the clicks settle
        // a group switched on or off: the idea on the card follows at once, same scene, the rest kept
        if ('hide' in body) refreshIdea();
        if (['themes', 'casts', 'ratings', 'sizes', 'kinks', 'acts', 'styles', 'allow_nsfw'].some((k) => k in body)) {
            clearTimeout(patch.t);
            patch.t = setTimeout(() => {
                const it = idea();
                if (M.open && M.view === 'idea' && (!it || !fits(it)) && countMatching()) nextIdea(false);
            }, 450);
        }
    }

    function toggleSwitch(label, on, change, hint) {
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

    function settingsView() {
        const s = st();
        const range = el('input', {type: 'range', min: '5', max: '30', step: '1', value: String(s.interval_minutes), 'aria-label': 'Minutes between ideas'});
        const rangeText = el('output', {text: s.interval_minutes + ' min'});
        range.addEventListener('input', () => { rangeText.textContent = range.value + ' min'; });
        range.addEventListener('change', () => patch({interval_minutes: +range.value}));

        const blacklist = el('textarea', {class: 'pv-muse-text', rows: '2', spellcheck: 'false', placeholder: 'e.g. hat, rain, red hair'});
        blacklist.value = s.blacklist || '';
        blacklist.addEventListener('change', () => patch({blacklist: blacklist.value}));

        const file = el('input', {type: 'file', accept: 'image/png,image/webp,image/jpeg,image/gif', hidden: true, onchange: onAvatar});

        return el('div', {class: 'pv-muse-body pv-muse-settings'},
            section('Timer',
                toggleSwitch('Bring ideas by themselves', s.enabled, (v) => patch({enabled: v}), 'never while an image is generating; the clock on top does the same'),
                el('div', {class: 'pv-muse-field' + (s.enabled ? '' : ' pv-muse-off')}, el('span', {class: 'pv-muse-field-label', text: 'Every'}), range, rangeText)),
            section('Parts',
                el('div', {class: 'pv-muse-hint', text: 'What ideas carry. Off: gone from the card and the prompt.'}),
                el('div', {class: 'pv-muse-switches'},
                    [['looks', 'Looks', 'build, skin, hair, eyes, makeup, gaze…'],
                        ['pet', 'Animals', 'a real animal with them (SFW only)'],
                        ['job', 'Job', 'an occupation, its clothes and props'],
                        ['action', 'Action', 'pose and what they do'],
                        ['light', 'Light', 'source, natural, quality, mood…'],
                        ['camera', 'Camera', 'shot, angle, viewpoint, framing'],
                        ['color', 'Color & grade', 'palettes, grading, film looks'],
                        ['style', 'Style', 'the medium: photo, anime, oil…']].map(([key, label, hint]) =>
                        toggleSwitch(label, !s.hide.includes(key), (v) => patch({hide: v ? s.hide.filter((h) => h !== key) : [...s.hide, key]}), hint)))),
            s.allow_nsfw ? section('NSFW',
                toggleSwitch('Body', s.anatomy, (v) => patch({anatomy: v}), 'breasts, pussy, penis, body hair, prosthetics… a part of NSFW ideas')) : null,
            section('Send',
                seg('How', 'send_mode', [['replace', 'Replace'], ['append', 'Append']]),
                seg('Generate', 'generate_in', [['txt2img', 'in txt2img'], ['img2img', 'in img2img']]),
                el('div', {class: 'pv-muse-hint', text: 'The card\'s Generate button writes the idea in that tab and presses its Generate: '
                    + 'your model, sampler, size and negative prompt as they are there. img2img uses the input image you put there.'})),
            qwenSection(),
            section('Arrange & describe',
                seg('Arrange', 'arrange_with', [['library', 'Library (instant)'], ['qwen', 'Qwen']]),
                seg('Describe', 'describe_as', [['both', 'Tags + text'], ['paragraph', 'Text only']]),
                el('div', {class: 'pv-muse-hint', text: 'Qwen is the model of the Vault tab: Settings → Prompt Vault (Qwen / llama-server).'})),
            section('TIPO',
                toggleSwitch('Show the TIPO button', s.use_tipo, (v) => patch({use_tipo: v}), 'expands an idea with the TIPO set up in the Vault tab'),
                s.use_tipo ? seg('Output', 'tipo_output', [['Tags', 'Tags'], ['Natural language', 'Words'], ['Tags + natural language', 'Both']]) : null,
                s.use_tipo ? seg('Length', 'tipo_length', [['very short', 'XS'], ['short', 'S'], ['long', 'L'], ['very long', 'XL']]) : null),
            section('Never use', blacklist,
                el('div', {class: 'pv-muse-hint', text: 'Comma-separated. Whole words only.'})),
            section('History',
                el('div', {class: 'pv-muse-field'},
                    el('span', {class: 'pv-muse-hint', text: `${M.ideas.length} of the last ${KEEP} ideas kept, in this browser`}),
                    el('button', {type: 'button', class: 'pv-btn', text: 'Clear the history', disabled: M.ideas.length < 2, onclick: clearHistory}))),
            section('Avatar',
                el('div', {class: 'pv-muse-avatar-row'}, avatarNode('pv-muse-face-lg'),
                    el('button', {type: 'button', class: 'pv-btn', text: 'Choose an image…', onclick: () => file.click()}), file,
                    M.snap.avatar.url ? el('button', {type: 'button', class: 'pv-btn', text: 'Remove', onclick: () => setAvatar(call('/muse/avatar/clear', {}))}) : null)),
            el('div', {class: 'pv-muse-hint', text: 'Scenes of your own: JSON files in prompt_vault/muse/scenes (see the README).'}));
    }

    // Qwen: which model and projector (from the .gguf files found), and where it lives (VRAM or RAM)
    async function loadQwen(body) {
        M.qwenBusy = true;
        try {
            if (body && body.__folders) {
                M.qwen = await call('/qwen/folders', {qwen_dirs: body.qwen_dirs, models_dir: body.models_dir});
                toast('Folders saved');
            } else {
                M.qwen = body ? await call('/qwen/models', body) : await call('/qwen/models');
            }
        } catch (e) {
            toast(e.message, true);
            if (!M.qwen) M.qwen = {models: [], mmprojs: [], memory_modes: [], dirs: [], error: e.message};
        }
        M.qwenBusy = false;
        if (M.view === 'settings') render();
    }

    function qwenSection() {
        const q = M.qwen;
        if (!q) {
            if (!M.qwenBusy) loadQwen();
            return section('Qwen model', el('div', {class: 'pv-muse-hint', text: 'Looking for .gguf files…'}));
        }
        const same = (a, b) => !!a && !!b && a.replace(/\\/g, '/').toLowerCase() === b.replace(/\\/g, '/').toLowerCase();
        const pick = (label, list, current, onchange, none) => {
            const known = list.some((m) => same(m.path, current));
            const groups = {};
            for (const m of list) (groups[m.folder] = groups[m.folder] || []).push(m);
            return el('label', {class: 'pv-muse-field pv-muse-pick'},
                el('span', {class: 'pv-muse-field-label', text: label}),
                el('select', {class: 'pv-muse-select', disabled: !!M.qwenBusy, onchange: (e) => onchange(e.target.value)},
                    el('option', {value: '', text: none, selected: !current}),
                    current && !known ? el('option', {value: current, text: current.split(/[\\/]/).pop() + ' (not in the folders below)', selected: true}) : null,
                    Object.entries(groups).map(([folder, ms]) => el('optgroup', {label: folder},
                        ms.map((m) => el('option', {value: m.path, title: m.path, text: `${m.name} · ${m.gb >= 0.1 ? m.gb + ' GB' : 'small'}`, selected: same(m.path, current)}))))));
        };
        return section('Qwen model',
            pick('Model', q.models, q.model, (v) => loadQwen({model: v}), q.models.length ? '— choose a model —' : '— no .gguf found —'),
            pick('Vision', q.mmprojs, q.mmproj, (v) => loadQwen({mmproj: v}), '— none: no images —'),
            el('label', {class: 'pv-muse-field pv-muse-pick'},
                el('span', {class: 'pv-muse-field-label', text: 'Lives in'}),
                el('select', {class: 'pv-muse-select', disabled: !!M.qwenBusy, onchange: (e) => loadQwen({memory: e.target.value}),
                    title: 'Auto: as much on the GPU as fits, the rest in RAM. Low VRAM: half (or a MoE model\'s experts) in RAM. RAM only: no VRAM, slow.'},
                (q.memory_modes || []).map((m) => el('option', {value: m, text: {Auto: 'Auto: VRAM as fits, the rest in RAM', 'All on GPU': 'All on the GPU',
                    'KV cache in RAM': 'GPU, the context in RAM', 'Low VRAM': 'Low VRAM: most in RAM', 'RAM only': 'RAM only (slow)'}[m] || m,
                selected: m === q.memory})))),
            toggleSwitch('Let it think first', !!q.think, (v) => loadQwen({think: v}),
                'Qwen Chat, with a model that reasons before answering (Qwen3.5, Qwen3.8…): better answers, much slower. Qwen3-VL Instruct does not think'),
            el('div', {class: 'pv-muse-field'},
                el('span', {class: 'pv-muse-hint', text: q.running ? `Running: ${q.note || ''}` : 'Starts when Qwen is first used; a new choice applies at once.'}),
                el('button', {type: 'button', class: 'pv-btn', text: '⟳', title: 'Look for .gguf files again', disabled: !!M.qwenBusy, onclick: () => loadQwen()})),
            el('div', {class: 'pv-muse-hint', text: 'Looked in: ' + ((q.dirs || []).join(' · ') || 'models/VLM (not there yet)')}),
            foldersView(q));
    }

    // where the models are: Qwen's .gguf files (one or more folders, any drive), and Prompt Vault's own (WD14, TIPO)
    function foldersView(q) {
        const qwenDirs = el('input', {type: 'text', class: 'pv-muse-text', spellcheck: 'false', value: q.qwen_dirs || '',
            placeholder: 'e.g. D:\\AI\\VLM; E:\\LLM (models/VLM is always looked through)'});
        const ownDir = el('input', {type: 'text', class: 'pv-muse-text', spellcheck: 'false', value: q.models_dir || '',
            placeholder: q.models_base || 'models/prompt_vault'});
        const save = () => loadQwen({__folders: true, qwen_dirs: qwenDirs.value, models_dir: ownDir.value});
        for (const box of [qwenDirs, ownDir]) box.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); save(); } });
        return el('div', {class: 'pv-muse-folders'},
            el('label', {class: 'pv-muse-field pv-muse-pick'}, el('span', {class: 'pv-muse-field-label', text: 'Qwen in'}), qwenDirs),
            el('label', {class: 'pv-muse-field pv-muse-pick'}, el('span', {class: 'pv-muse-field-label', text: 'WD14, TIPO'}), ownDir),
            (q.missing || []).length ? el('div', {class: 'pv-muse-hint pv-muse-warn', text: 'Not found: ' + q.missing.join('; ')}) : null,
            el('div', {class: 'pv-muse-field'},
                el('span', {class: 'pv-muse-hint', text: 'Any drive. Several Qwen folders: separate them with ;. Moving the WD14 and TIPO '
                    + 'models: move their folders (wd14, tipo) yourself, then set the new place here.'}),
                el('button', {type: 'button', class: 'pv-btn', text: 'Save folders', disabled: !!M.qwenBusy, onclick: save})));
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
        panel.classList.toggle('pv-muse-wide', isWide());
        const chat = M.view !== 'settings' && M.pane === 'chat';
        panel.classList.toggle('pv-muse-chatting', chat);
        panel.replaceChildren(...[header(), M.view === 'settings' ? null : panes(),
            ...(M.view === 'settings' ? [settingsView()] : chat ? [chatView()] : [ideaView(), ideaFooter()])].filter(Boolean));
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
        fab.title = 'Muse: ' + (statusText() || 'ideas');
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
        addEventListener('resize', () => {
            restore();
            if (M.open && M.wide && !!$('#pv_muse_panel.pv-muse-wide') !== isWide()) render();
        });
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

    // for Qwen Chat: the idea on the card, and Your prompt to build around
    window.pvMuse = {
        prompt: () => (idea() ? fullPrompt(idea()) : ''),
        setOwn: async (value) => {
            await patch({fixed_prompt: value, prompt_mode: 'around'});
            if (M.open) { M.pane = 'ideas'; LS.set('pane', 'ideas'); render(); }
        },
    };

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
