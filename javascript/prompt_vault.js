// Prompt Vault: the tag library, saved prompts, history and suggestions, drawn in the browser.
// The Python side (lib_vault/api.py) keeps the data; this file only shows it and sends changes.

(() => {
    'use strict';

    const API = '/prompt-vault/api';
    const LS = {
        get(key, fallback) { try { const v = localStorage.getItem('pv_' + key); return v === null ? fallback : JSON.parse(v); } catch (e) { return fallback; } },
        set(key, value) { try { localStorage.setItem('pv_' + key, JSON.stringify(value)); } catch (e) { /* private window */ } },
    };
    const S = {
        lib: null,              // {categories: [{name, nsfw, negative, groups: [{name, tags}]}], count, folder}
        open: new Set(LS.get('open', [])),
        edit: false,
        hideNsfw: null,
        search: '',
        vocab: null,
        savedTab: LS.get('saved_tab', 'saved'),
    };

    const app = () => (typeof gradioApp === 'function' ? gradioApp() : document);
    const $ = (sel, root) => (root || app()).querySelector(sel);
    const el = (tag, attrs, ...children) => {
        const node = document.createElement(tag);
        for (const [k, v] of Object.entries(attrs || {})) {
            if (v === undefined || v === null || v === false) continue;
            if (k === 'class') node.className = v;
            else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
            else if (k === 'text') node.textContent = v;
            else node.setAttribute(k, v === true ? '' : v);
        }
        for (const c of children.flat()) if (c !== null && c !== undefined && c !== false) node.append(c);
        return node;
    };

    // pop-ups go inside the Gradio container: they take its font and theme colours there
    const layer = () => document.querySelector('.gradio-container') || document.body;

    function root() {
        const r = (window.gradio_config && window.gradio_config.root) || '';
        return r.replace(/\/$/, '');
    }

    async function call(path, body) {
        const opts = body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)};
        const res = await fetch(root() + API + path, opts);
        let data = null;
        try { data = await res.json(); } catch (e) { /* not json */ }
        if (!res.ok) throw new Error((data && data.error) || ('HTTP ' + res.status));
        return data;
    }

    function toast(message, bad) {
        const box = $('#pv_toast') || layer().appendChild(el('div', {id: 'pv_toast'}));
        box.textContent = message;
        box.className = 'pv-show' + (bad ? ' pv-bad' : '');
        clearTimeout(toast.t);
        toast.t = setTimeout(() => { box.className = ''; }, bad ? 5000 : 2200);
    }

    // ------------------------------------------------------------------ prompt pieces (same rules as lib_vault/text.py)

    function split(prompt) {
        const pieces = []; let depth = 0, cur = '', esc = false;
        for (const ch of prompt || '') {
            if (esc) { cur += ch; esc = false; continue; }
            if (ch === '\\') { cur += ch; esc = true; continue; }
            if ('([{<'.includes(ch)) depth++;
            else if (')]}>'.includes(ch) && depth) depth--;
            if ((ch === ',' || ch === '\n') && depth === 0) { pieces.push(cur); cur = ''; continue; }
            cur += ch;
        }
        pieces.push(cur);
        return pieces.map((p) => p.trim()).filter(Boolean);
    }

    const WEIGHT = /^\(([\s\S]*):\s*([-+]?\d*\.?\d+)\s*\)$/;

    function key(piece) {
        let s = (piece || '').trim();
        for (let i = 0; i < 4; i++) {
            const m = s.match(WEIGHT);
            if (m) { s = m[1].trim(); continue; }
            if (s.length > 2 && ((s[0] === '(' && s.endsWith(')') && !s.endsWith('\\)')) || (s[0] === '[' && s.endsWith(']')))) { s = s.slice(1, -1).trim(); continue; }
            break;
        }
        return s.replace(/\\\(/g, '(').replace(/\\\)/g, ')').replace(/_/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
    }

    function dedupePrompt(prompt) {
        const seen = new Set();
        const out = [];
        for (const piece of split(prompt)) {
            const k = key(piece);
            if (!k || seen.has(k)) continue;
            seen.add(k);
            out.push(piece);
        }
        return out.join(', ');
    }

    function dedupeBox(area) {
        if (!area) return;
        const next = dedupePrompt(area.value);
        if (next === area.value) return;
        area.value = next;
        if (typeof updateInput === 'function') updateInput(area);
        else area.dispatchEvent(new Event('input', {bubbles: true}));
    }
        const m = (piece || '').trim().match(WEIGHT);
        if (m) return parseFloat(m[2]);
        let s = (piece || '').trim(), w = 1;
        while (s.length > 2 && s[0] === '(' && s.endsWith(')') && !s.endsWith('\\)')) { w *= 1.1; s = s.slice(1, -1); }
        return Math.round(w * 100) / 100;
    }

    // ------------------------------------------------------------------ the editor boxes

    const box = (which) => $(which === 'negative' ? '#pv_negative textarea' : '#pv_positive textarea');

    function setBox(area, value) {
        area.value = value;
        if (typeof updateInput === 'function') updateInput(area);
        else area.dispatchEvent(new Event('input', {bubbles: true}));
        refreshMarks();
    }

    function keysIn(which) {
        const area = box(which);
        return new Set(area ? split(area.value).map(key) : []);
    }

    function toggleTag(tag, which) {
        const area = box(which);
        if (!area) return;
        const pieces = split(area.value);
        const k = key(tag);
        const at = pieces.findIndex((p) => key(p) === k);
        if (at >= 0) {
            pieces.splice(at, 1);
            setBox(area, pieces.join(', '));
        } else {
            const current = area.value.replace(/[\s,]+$/, '');
            setBox(area, current ? current + ', ' + tag : tag);
        }
    }

    function setWeight(tag, which, weight) {
        const area = box(which);
        const pieces = split(area.value);
        const k = key(tag);
        const at = pieces.findIndex((p) => key(p) === k);
        if (at < 0) return;
        let bare = pieces[at];
        for (let i = 0; i < 6; i++) {
            const m = bare.match(WEIGHT);
            if (m) { bare = m[1].trim(); continue; }
            if (bare.length > 2 && bare[0] === '(' && bare.endsWith(')') && !bare.endsWith('\\)')) { bare = bare.slice(1, -1).trim(); continue; }
            break;
        }
        weight = Math.round(weight * 100) / 100;
        pieces[at] = Math.abs(weight - 1) < 0.001 ? bare : `(${bare}:${weight})`;
        setBox(area, pieces.join(', '));
    }

    // ------------------------------------------------------------------ library

    async function loadLibrary() {
        try {
            S.lib = await call('/library');
            renderLibrary();
        } catch (e) {
            const host = $('#pv_library');
            if (host) host.innerHTML = '<div class="pv-loading">The library could not be loaded: ' + e.message + '</div>';
        }
    }

    function applyChange(promise, done) {
        return promise.then((info) => {
            if (info && info.categories) S.lib = info;
            S.vocab = null;
            renderLibrary();
            if (done) toast(done);
            return info;
        }).catch((e) => { toast(e.message, true); throw e; });
    }

    const edit = (op, args, done) => applyChange(call('/library/edit', Object.assign({op}, args)), done);

    function isHidden(cat) { return S.hideNsfw && cat.nsfw; }

    function chip(tag, cat, group) {
        const which = cat.negative ? 'negative' : 'positive';
        const node = el('button', {class: 'pv-chip', type: 'button', title: tag, 'data-key': key(tag), 'data-box': which, text: tag});
        node.addEventListener('click', (ev) => {
            if (S.edit) { tagDialog(tag, cat, group); return; }
            const target = ev.shiftKey ? (which === 'negative' ? 'positive' : 'negative') : which;
            toggleTag(tag, target);
        });
        node.addEventListener('contextmenu', (ev) => {
            if (S.edit) return;
            const target = keysIn('negative').has(key(tag)) && !keysIn('positive').has(key(tag)) ? 'negative' : which;
            if (!keysIn(target).has(key(tag))) return;
            ev.preventDefault();
            weightPopup(node, tag, target);
        });
        return node;
    }

    function groupBlock(cat, group) {
        const head = el('div', {class: 'pv-group-head'},
            el('span', {class: 'pv-group-name', text: group.name}),
            el('span', {class: 'pv-count', text: String(group.tags.length)}));
        if (S.edit) {
            head.append(
                el('button', {class: 'pv-mini', type: 'button', title: 'Add tags', text: '＋', onclick: () => addTagsDialog(cat, group)}),
                el('button', {class: 'pv-mini', type: 'button', title: 'Rename or move the group', text: '✏️', onclick: () => groupDialog(cat, group)}),
                el('button', {class: 'pv-mini', type: 'button', title: 'Delete the group', text: '🗑️', onclick: () => {
                    if (confirm(`Delete the group “${group.name}” and its ${group.tags.length} tags?`)) edit('delete_group', {category: cat.name, group: group.name}, 'Group deleted');
                }}));
        }
        const chips = el('div', {class: 'pv-chips'}, group.tags.map((t) => chip(t, cat, group)));
        if (!group.tags.length) chips.append(el('span', {class: 'pv-empty', text: S.edit ? 'empty: ＋ adds tags' : 'empty'}));
        return el('div', {class: 'pv-group'}, head, chips);
    }

    function categoryBlock(cat, index) {
        const isOpen = S.open.has(cat.name);
        const count = cat.groups.reduce((n, g) => n + g.tags.length, 0);
        const head = el('div', {class: 'pv-cat-head' + (isOpen ? ' pv-open' : '')},
            el('button', {class: 'pv-cat-toggle', type: 'button', onclick: () => {
                if (S.open.has(cat.name)) S.open.delete(cat.name); else S.open.add(cat.name);
                LS.set('open', [...S.open]);
                renderLibrary();
            }},
            el('span', {class: 'pv-arrow', text: isOpen ? '▾' : '▸'}),
            el('span', {class: 'pv-cat-name', text: cat.name}),
            cat.negative ? el('span', {class: 'pv-badge', text: 'negative'}) : null,
            el('span', {class: 'pv-count', text: `${cat.groups.length} groups · ${count}`})));
        if (S.edit) {
            head.append(
                el('button', {class: 'pv-mini', type: 'button', title: 'Add a group', text: '＋', onclick: () => {
                    dialog('New group in ' + cat.name, [{name: 'new', label: 'Name'}], (v) => edit('add_group', {category: cat.name, new: v.new}, 'Group added'));
                }}),
                el('button', {class: 'pv-mini', type: 'button', title: 'Rename', text: '✏️', onclick: () => {
                    dialog('Rename category', [{name: 'new', label: 'Name', value: cat.name}], (v) => {
                        const wasOpen = S.open.delete(cat.name);
                        if (wasOpen) S.open.add(v.new);
                        return edit('rename_category', {category: cat.name, new: v.new}, 'Renamed');
                    });
                }}),
                el('button', {class: 'pv-mini', type: 'button', title: 'Move up', text: '↑', disabled: index === 0, onclick: () => edit('move_category', {category: cat.name, direction: 'up'})}),
                el('button', {class: 'pv-mini', type: 'button', title: 'Move down', text: '↓', disabled: index === S.lib.categories.length - 1, onclick: () => edit('move_category', {category: cat.name, direction: 'down'})}),
                el('button', {class: 'pv-mini', type: 'button', title: 'Delete the category', text: '🗑️', onclick: () => {
                    if (confirm(`Delete the category “${cat.name}” with all its groups and ${count} tags?`)) edit('delete_category', {category: cat.name}, 'Category deleted');
                }}));
        }
        const block = el('div', {class: 'pv-cat'}, head);
        if (isOpen) block.append(el('div', {class: 'pv-groups'}, cat.groups.map((g) => groupBlock(cat, g))));
        return block;
    }

    function searchResults() {
        const q = key(S.search);
        const hits = [];
        for (const cat of S.lib.categories) {
            if (isHidden(cat)) continue;
            for (const group of cat.groups) {
                for (const t of group.tags) if (key(t).includes(q)) hits.push([t, cat, group]);
            }
        }
        hits.sort((a, b) => (key(a[0]).startsWith(q) ? 0 : 1) - (key(b[0]).startsWith(q) ? 0 : 1));
        const shown = hits.slice(0, 400);
        const list = el('div', {class: 'pv-results'},
            el('div', {class: 'pv-hint', text: hits.length ? `${hits.length} tags${hits.length > shown.length ? ', the first 400 shown' : ''}` : 'No tag in the library matches.'}),
            el('div', {class: 'pv-chips'}, shown.map(([t, cat, group]) => {
                const c = chip(t, cat, group);
                c.title = `${cat.name} › ${group.name}`;
                return c;
            })));
        if (!hits.length && S.search.trim()) {
            list.append(el('button', {class: 'pv-btn', type: 'button', text: `＋ Add “${S.search.trim()}” to the library`, onclick: () => addAnywhereDialog(S.search.trim())}));
        }
        return list;
    }

    function toolbar() {
        const search = el('input', {class: 'pv-search', type: 'search', placeholder: `Search ${S.lib.count} tags…`, value: S.search});
        search.addEventListener('input', () => {
            S.search = search.value;
            clearTimeout(toolbar.t);
            toolbar.t = setTimeout(() => {
                renderLibrary();
                const again = $('#pv_library .pv-search');
                if (again) { again.focus(); again.setSelectionRange(again.value.length, again.value.length); }
            }, 120);
        });
        const hide = el('label', {class: 'pv-switch', title: 'Hide the categories with NSFW in their name'},
            el('input', {type: 'checkbox', checked: S.hideNsfw, onchange: (e) => { S.hideNsfw = e.target.checked; LS.set('hide_nsfw', S.hideNsfw); renderLibrary(); }}),
            el('span', {text: 'Hide NSFW'}));
        const editSwitch = el('label', {class: 'pv-switch', title: 'Add, rename, move and delete tags, groups and categories'},
            el('input', {type: 'checkbox', checked: S.edit, onchange: (e) => { S.edit = e.target.checked; renderLibrary(); }}),
            el('span', {text: 'Edit the library'}));
        const bar = el('div', {class: 'pv-toolbar'},
            search,
            el('div', {class: 'pv-toolbar-row'},
                hide, editSwitch,
                el('button', {class: 'pv-btn', type: 'button', text: 'Open all', onclick: () => { S.lib.categories.forEach((c) => S.open.add(c.name)); LS.set('open', [...S.open]); renderLibrary(); }}),
                el('button', {class: 'pv-btn', type: 'button', text: 'Close all', onclick: () => { S.open.clear(); LS.set('open', []); renderLibrary(); }})));
        if (S.edit) {
            const file = el('input', {type: 'file', accept: '.json,application/json', style: 'display:none', onchange: (e) => importFile(e.target.files[0])});
            bar.append(el('div', {class: 'pv-toolbar-row pv-edit-row'},
                el('button', {class: 'pv-btn', type: 'button', text: '＋ Category', onclick: () => dialog('New category', [{name: 'new', label: 'Name'}], (v) => edit('add_category', {new: v.new}, 'Category added'))}),
                el('button', {class: 'pv-btn', type: 'button', text: '📥 Import…', onclick: () => file.click()}), file,
                el('a', {class: 'pv-btn', href: root() + API + '/library/export', download: 'prompt-vault-library.json', text: '📤 Export'}),
                el('button', {class: 'pv-btn', type: 'button', text: '🧺 Add missing default tags', title: 'Adds what the library that ships with the extension has and yours does not. Removes nothing.', onclick: () => {
                    applyChange(call('/library/merge-defaults', {})).then((info) => toast(info.added ? `${info.added} tags added` : 'Nothing was missing'));
                }})),
            el('div', {class: 'pv-hint', text: `Click a tag to rename, move or delete it. Saved in ${S.lib.folder}, with backups.`}));
        }
        return bar;
    }

    function renderLibrary() {
        const host = $('#pv_library');
        if (!host || !S.lib) return;
        if (S.hideNsfw === null) S.hideNsfw = LS.get('hide_nsfw', !!(window.opts && opts.pv_hide_nsfw));
        const body = el('div', {class: 'pv-lib' + (S.edit ? ' pv-editing' : '')},
            el('div', {class: 'pv-title'}, el('span', {text: '🏷️ Library'}),
                el('span', {class: 'pv-hint', text: 'Click: add or remove · Shift+click: the other prompt · Right-click an added tag: weight'})),
            toolbar());
        if (S.search.trim()) body.append(searchResults());
        else S.lib.categories.forEach((cat, i) => { if (!isHidden(cat)) body.append(categoryBlock(cat, i)); });
        host.replaceChildren(body);
        refreshMarks();
    }

    function refreshMarks() {
        const host = $('#pv_library');
        if (!host) return;
        const on = {positive: keysIn('positive'), negative: keysIn('negative')};
        host.querySelectorAll('.pv-chip').forEach((c) => {
            const k = c.dataset.key;
            c.classList.toggle('pv-on', on[c.dataset.box].has(k));
            c.classList.toggle('pv-on-other', !on[c.dataset.box].has(k) && on[c.dataset.box === 'positive' ? 'negative' : 'positive'].has(k));
        });
    }

    // ------------------------------------------------------------------ small dialogs

    function dialog(title, fields, ok) {
        closeDialog();
        const inputs = {};
        const form = el('form', {class: 'pv-dialog'}, el('div', {class: 'pv-dialog-title', text: title}));
        for (const f of fields) {
            let input;
            if (f.options) {
                input = el('select', {}, f.options.map((o) => el('option', {value: o, text: o, selected: o === f.value})));
                if (f.onchange) input.addEventListener('change', () => f.onchange(input.value, inputs));
            } else {
                input = el(f.multiline ? 'textarea' : 'input', {type: 'text', placeholder: f.placeholder || ''});
                input.value = f.value || '';
            }
            // take the editor's own look: every theme (Lobe too) styles its textareas, not ours
            const ref = box('positive');
            if (ref) {
                const cs = getComputedStyle(ref);
                input.style.backgroundColor = cs.backgroundColor;
                input.style.color = cs.color;
            }
            inputs[f.name] = input;
            form.append(el('label', {}, el('span', {text: f.label}), input));
        }
        const buttons = el('div', {class: 'pv-dialog-buttons'},
            el('button', {class: 'pv-btn', type: 'button', text: 'Cancel', onclick: closeDialog}),
            el('button', {class: 'pv-btn pv-primary', type: 'submit', text: 'OK'}));
        form.append(buttons);
        form.addEventListener('submit', (ev) => {
            ev.preventDefault();
            const values = {};
            for (const [k, input] of Object.entries(inputs)) values[k] = input.value.trim();
            Promise.resolve(ok(values)).then(closeDialog).catch(() => { /* toast shown; keep the dialog */ });
        });
        form.addEventListener('keydown', (ev) => { if (ev.key === 'Escape') closeDialog(); });
        const shade = el('div', {class: 'pv-shade', onclick: (e) => { if (e.target === shade) closeDialog(); }}, form);
        layer().append(shade);
        const first = form.querySelector('input, textarea, select');
        if (first) first.focus();
        return inputs;
    }

    function closeDialog() {
        document.querySelectorAll('.pv-shade').forEach((n) => n.remove());
    }

    const categoryNames = () => S.lib.categories.map((c) => c.name);
    const groupNames = (catName) => ((S.lib.categories.find((c) => c.name === catName) || {groups: []}).groups.map((g) => g.name));

    function tagDialog(tag, cat, group) {
        const cats = categoryNames();
        dialog(`“${tag}” in ${cat.name} › ${group.name}`, [
            {name: 'new', label: 'Tag', value: tag},
            {name: 'category', label: 'Category', options: cats, value: cat.name, onchange: (v, inputs) => {
                inputs.group.replaceChildren(...groupNames(v).map((g) => el('option', {value: g, text: g})));
            }},
            {name: 'group', label: 'Group', options: groupNames(cat.name), value: group.name},
        ], async (v) => {
            let current = tag;
            if (v.new && v.new !== tag) {
                await edit('rename_tag', {category: cat.name, group: group.name, tag, new: v.new});
                current = v.new;
            }
            if (v.category !== cat.name || v.group !== group.name) {
                await edit('move_tag', {category: cat.name, group: group.name, tag: current, to_category: v.category, to_group: v.group});
            }
            toast('Saved');
        });
        const form = $('.pv-dialog', document);
        form.querySelector('.pv-dialog-buttons').prepend(el('button', {class: 'pv-btn pv-danger', type: 'button', text: '🗑️ Delete', onclick: () => {
            edit('remove_tag', {category: cat.name, group: group.name, tag}, 'Tag deleted').then(closeDialog);
        }}));
    }

    function groupDialog(cat, group) {
        dialog(`Group “${group.name}”`, [
            {name: 'new', label: 'Name', value: group.name},
            {name: 'category', label: 'Category', options: categoryNames(), value: cat.name},
        ], async (v) => {
            let name = group.name;
            if (v.new && v.new !== group.name) {
                await edit('rename_group', {category: cat.name, group: group.name, new: v.new});
                name = v.new;
            }
            if (v.category !== cat.name) await edit('move_group', {category: cat.name, group: name, to_category: v.category});
            toast('Saved');
        });
    }

    function addTagsDialog(cat, group) {
        dialog(`Add tags to ${cat.name} › ${group.name}`, [
            {name: 'tags', label: 'Tags, comma-separated', multiline: true, placeholder: 'volumetric fog, (rim light:1.1)'},
        ], (v) => edit('add_tags', {category: cat.name, group: group.name, tags: v.tags}, 'Added'));
    }

    function addAnywhereDialog(tags) {
        const cats = categoryNames();
        const lastCat = LS.get('last_cat', cats[0]);
        const firstCat = cats.includes(lastCat) ? lastCat : cats[0];
        const groups = groupNames(firstCat);
        const lastGroup = LS.get('last_group', groups[0]);
        dialog('Add to the library', [
            {name: 'tags', label: 'Tags, comma-separated', value: tags, multiline: true},
            {name: 'category', label: 'Category', options: cats, value: firstCat, onchange: (v, inputs) => {
                inputs.group.replaceChildren(...groupNames(v).map((g) => el('option', {value: g, text: g})));
            }},
            {name: 'group', label: 'Group', options: groups, value: groups.includes(lastGroup) ? lastGroup : groups[0]},
        ], (v) => {
            LS.set('last_cat', v.category);
            LS.set('last_group', v.group);
            return edit('add_tags', {category: v.category, group: v.group, tags: v.tags}, 'Added to the library');
        });
    }

    function importFile(file) {
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            let data;
            try { data = JSON.parse(reader.result); } catch (e) { toast('That file is not JSON', true); return; }
            dialog('Import ' + file.name, [
                {name: 'mode', label: 'How', options: ['Merge into my library', 'Replace my library'], value: 'Merge into my library'},
            ], (v) => applyChange(call('/library/import', {data, mode: v.mode.startsWith('Replace') ? 'replace' : 'merge'}), 'Imported'));
        };
        reader.readAsText(file);
    }

    function weightPopup(anchor, tag, which) {
        document.querySelectorAll('.pv-weight').forEach((n) => n.remove());
        const area = box(which);
        const piece = split(area.value).find((p) => key(p) === key(tag));
        let w = weightOf(piece);
        const value = el('span', {class: 'pv-weight-value', text: w.toFixed(2)});
        const change = (d) => { w = Math.max(0, Math.round((w + d) * 100) / 100); value.textContent = w.toFixed(2); setWeight(tag, which, w); };
        const pop = el('div', {class: 'pv-weight'},
            el('button', {class: 'pv-mini', type: 'button', text: '−', onclick: () => change(-0.1)}),
            value,
            el('button', {class: 'pv-mini', type: 'button', text: '+', onclick: () => change(0.1)}),
            el('button', {class: 'pv-mini', type: 'button', text: '1', title: 'No weight', onclick: () => { w = 1; value.textContent = '1.00'; setWeight(tag, which, 1); }}),
            el('button', {class: 'pv-mini', type: 'button', text: '✕', title: 'Remove from the prompt', onclick: () => { toggleTag(tag, which); pop.remove(); }}));
        const r = anchor.getBoundingClientRect();
        pop.style.left = Math.max(8, Math.min(window.innerWidth - 230, r.left)) + 'px';
        layer().append(pop);
        const h = pop.offsetHeight || 46;
        pop.style.top = (r.bottom + 4 + h > window.innerHeight ? Math.max(4, r.top - h - 4) : r.bottom + 4) + 'px';
        window.addEventListener('scroll', () => pop.remove(), {once: true, capture: true});
        const away = (ev) => { if (!pop.contains(ev.target)) { pop.remove(); document.removeEventListener('mousedown', away, true); } };
        setTimeout(() => document.addEventListener('mousedown', away, true), 0);
    }

    // ------------------------------------------------------------------ saved prompts and history

    async function reloadSaved() {
        const host = $('#pv_saved');
        if (!host) return;
        try {
            const [saved, history] = await Promise.all([call('/prompts'), call('/history')]);
            renderSaved(saved.prompts || [], history.history || []);
        } catch (e) {
            host.textContent = 'Could not load: ' + e.message;
        }
    }

    function load(entry) {
        setBox(box('positive'), entry.positive || '');
        setBox(box('negative'), entry.negative || '');
        toast('In the editor');
    }

    function when(t) {
        if (!t) return '';
        const d = new Date(t * 1000);
        return d.toLocaleString(undefined, {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'});
    }

    function entryRow(entry, actions, title) {
        return el('div', {class: 'pv-entry'},
            entry.thumb ? el('img', {class: 'pv-thumb', src: entry.thumb, alt: ''}) : null,
            el('div', {class: 'pv-entry-text'},
                el('div', {class: 'pv-entry-title', text: title}),
                el('div', {class: 'pv-entry-prompt', text: entry.positive || '(no positive prompt)', title: entry.positive || ''}),
                entry.negative ? el('div', {class: 'pv-entry-neg', text: '− ' + entry.negative, title: entry.negative}) : null),
            el('div', {class: 'pv-entry-actions'}, actions));
    }

    function renderSaved(saved, history) {
        const host = $('#pv_saved');
        const tabs = el('div', {class: 'pv-toolbar-row'},
            el('button', {class: 'pv-btn' + (S.savedTab === 'saved' ? ' pv-primary' : ''), type: 'button', text: `Saved (${saved.length})`, onclick: () => { S.savedTab = 'saved'; LS.set('saved_tab', 'saved'); renderSaved(saved, history); }}),
            el('button', {class: 'pv-btn' + (S.savedTab === 'history' ? ' pv-primary' : ''), type: 'button', text: `History (${history.length})`, onclick: () => { S.savedTab = 'history'; LS.set('saved_tab', 'history'); renderSaved(saved, history); }}),
            el('button', {class: 'pv-btn', type: 'button', text: '⟳ Reload', title: 'Reload', onclick: reloadSaved}));
        const list = el('div', {class: 'pv-entries'});
        if (S.savedTab === 'saved') {
            if (!saved.length) list.append(el('div', {class: 'pv-hint', text: 'Nothing saved yet: give the editor a name above and press Save.'}));
            for (const p of saved) {
                list.append(entryRow(p, [
                    el('button', {class: 'pv-btn pv-primary', type: 'button', text: 'Load', onclick: () => load(p)}),
                    el('button', {class: 'pv-btn', type: 'button', text: 'Rename', onclick: () => dialog('Rename', [{name: 'new', label: 'Name', value: p.name}], (v) => call('/prompts/edit', {op: 'rename', id: p.id, new: v.new}).then(reloadSaved).catch((e) => { toast(e.message, true); throw e; }))}),
                    el('button', {class: 'pv-btn pv-danger', type: 'button', text: 'Delete', onclick: () => { if (confirm(`Delete “${p.name}”?`)) call('/prompts/edit', {op: 'delete', id: p.id}).then(reloadSaved); }}),
                ], p.name));
            }
        } else {
            if (!history.length) {
                const on = !(window.opts && opts.pv_history === false);
                list.append(el('div', {class: 'pv-hint', text: on ? 'The prompts of your generations show up here.' : 'History is off (Settings → Prompt Vault).'}));
            } else {
                list.append(el('div', {}, el('button', {class: 'pv-btn pv-danger', type: 'button', text: 'Clear the history', onclick: () => { if (confirm('Clear the whole history?')) call('/history/clear', {}).then(reloadSaved); }})));
            }
            for (const h of history) {
                const title = `${when(h.time)}${h.tab ? ' · ' + h.tab : ''}${h.count > 1 ? ' · ×' + h.count : ''}`;
                list.append(entryRow(h, [
                    el('button', {class: 'pv-btn pv-primary', type: 'button', text: 'Load', onclick: () => load(h)}),
                    el('button', {class: 'pv-btn', type: 'button', text: 'Save…', onclick: () => { load(h); const n = $('#pv_save_name textarea, #pv_save_name input'); if (n) n.focus(); }}),
                ], title));
            }
        }
        host.replaceChildren(el('div', {class: 'pv-saved'}, tabs, list));
    }

    function watchGenerate() {
        for (const tab of ['txt2img', 'img2img']) {
            const button = $('#' + tab + '_generate');
            if (!button || button.dataset.pvWatched) continue;
            button.dataset.pvWatched = '1';
            button.addEventListener('click', () => {
                dedupeBox($('#' + tab + '_prompt textarea'));
                dedupeBox($('#' + tab + '_neg_prompt textarea'));
                if (window.opts && opts.pv_history === false) return;
                const get = (id) => { const a = $('#' + id + ' textarea'); return a ? a.value : ''; };
                const positive = get(tab + '_prompt'), negative = get(tab + '_neg_prompt');
                if (!positive.trim() && !negative.trim()) return;
                call('/history/add', {positive, negative, tab}).catch(() => { /* never in the way of a generation */ });
            }, true);
        }
    }

    // ------------------------------------------------------------------ suggestions while typing

    async function vocab() {
        if (S.vocab) return S.vocab;
        const data = await call('/vocab');
        S.vocab = data.tags.map(([t, cat, count]) => ({t, k: t.toLowerCase(), cat, count}));
        S.vocabDanbooru = S.vocab.some((v) => v.cat !== 'vault');
        return S.vocab;
    }

    function fragment(area) {
        const upto = area.value.slice(0, area.selectionStart);
        const start = Math.max(upto.lastIndexOf(','), upto.lastIndexOf('\n')) + 1;
        const raw = upto.slice(start);
        const lead = raw.match(/^\s*[\(\[]*/)[0];
        return {start: start + lead.length, text: raw.slice(lead.length)};
    }

    // a list of tags under a box while you type in it: the editor here, the WebUI's prompts if you want,
    // and Muse's boxes (window.promptVault.attachSuggest). onAccept: after a tag is put in.
    function attachSuggest(area, onAccept) {
        if (!area || !area.parentElement || area.dataset.pvSuggest) return;
        area.dataset.pvSuggest = '1';
        const list = el('div', {class: 'pv-suggest'});
        list.style.display = 'none';
        area.parentElement.style.position = 'relative';
        area.parentElement.append(list);
        let items = [], active = 0;

        const close = () => { list.style.display = 'none'; items = []; };
        const accept = (i) => {
            const it = items[i];
            if (!it) return;
            const f = fragment(area);
            // the rest of the piece being typed goes, the pieces after it stay
            const rest = area.value.slice(area.selectionStart).replace(/^[^,\n]*/, '').replace(/^\s*,?\s*/, '');
            const insert = it.t + ', ';
            setBox(area, area.value.slice(0, f.start) + insert + rest);
            const caret = f.start + insert.length;
            area.setSelectionRange(caret, caret);
            close();
            if (onAccept) onAccept(area);
        };
        const draw = () => {
            list.replaceChildren(...items.map((it, i) => el('div', {class: 'pv-suggest-item' + (i === active ? ' pv-active' : ''),
                onmousedown: (e) => { e.preventDefault(); accept(i); }},
                el('span', {text: it.t}),
                el('span', {class: 'pv-suggest-cat pv-cat-' + it.cat, text: it.cat === 'vault' ? 'library' : it.cat + (it.count ? ' · ' + (it.count >= 1000 ? Math.round(it.count / 1000) + 'k' : it.count) : '')}))));
            list.style.display = items.length ? 'block' : 'none';
        };
        area.addEventListener('input', async () => {
            if (window.opts && opts.pv_autocomplete === false) return;
            if (document.activeElement !== area) { close(); return; } // written by a button, not typed: no suggestions
            const f = fragment(area);
            const q = f.text.trim().toLowerCase().replace(/_/g, ' ');
            if (q.length < 2) { close(); return; }
            let words;
            try { words = await vocab(); } catch (e) { return; }
            const starts = [], contains = [];
            for (const v of words) {
                if (v.k.startsWith(q)) starts.push(v);
                else if (contains.length < 40 && v.k.includes(q)) contains.push(v);
            }
            const rank = (a, b) => (b.cat === 'vault') - (a.cat === 'vault') || b.count - a.count;
            items = starts.sort(rank).concat(contains.sort(rank)).filter((v) => v.k !== q).slice(0, 10);
            active = 0;
            draw();
        });
        area.addEventListener('keydown', (ev) => {
            if (!items.length || list.style.display === 'none') return;
            if (ev.key === 'ArrowDown') { active = (active + 1) % items.length; draw(); ev.preventDefault(); }
            else if (ev.key === 'ArrowUp') { active = (active - 1 + items.length) % items.length; draw(); ev.preventDefault(); }
            else if (ev.key === 'Enter' || ev.key === 'Tab') { accept(active); ev.preventDefault(); ev.stopImmediatePropagation(); }
            else if (ev.key === 'Escape') { close(); ev.preventDefault(); ev.stopImmediatePropagation(); }
        }, true);
        area.addEventListener('blur', () => setTimeout(close, 150));
    }

    // ------------------------------------------------------------------ editor tools

    function editorTools() {
        const host = $('#pv_editor_tools');
        if (!host || host.dataset.pvReady) return;
        host.dataset.pvReady = '1';
        const out = el('div', {class: 'pv-check'});
        host.append(el('div', {class: 'pv-toolbar-row'},
            el('button', {class: 'pv-btn', type: 'button', text: '🔍 Check tags', title: 'Tags that are neither in your library nor known Danbooru tags', onclick: checkTags}),
            el('button', {class: 'pv-btn', type: 'button', text: '💡 Muse idea', title: 'An idea from Muse, with the filters set on its card, into the editor', onclick: () => {
                call('/muse/next', {}).then((d) => {
                    setBox(box('positive'), d.idea.positive);
                    const neg = box('negative');
                    const have = new Set(split(neg.value).map(key));
                    const extra = split(d.idea.negative || '').filter((p) => !have.has(key(p)));
                    if (extra.length) setBox(neg, neg.value.replace(/[\s,]+$/, '') + (neg.value.trim() ? ', ' : '') + extra.join(', '));
                    toast('Muse: ' + d.idea.title);
                }).catch((e) => toast(e.message, true));
            }}),
            el('button', {class: 'pv-btn', type: 'button', text: '🗂️ Arrange', title: 'Put the tags in order (quality, who, body, face, clothes, pose, place, light, camera, style) from what your library knows of them; duplicates go', onclick: () => {
                const area = box('positive');
                if (!area.value.trim()) return;
                call('/prompt/arrange', {prompt: area.value}).then((d) => { setBox(area, d.result); toast(d.note); }).catch((e) => toast(e.message, true));
            }}),
            el('button', {class: 'pv-btn', type: 'button', text: '🧽 Remove duplicates', onclick: () => {
                for (const which of ['positive', 'negative']) {
                    const area = box(which);
                    const seen = new Set(), keep = [];
                    for (const p of split(area.value)) { const k = key(p); if (!seen.has(k)) { seen.add(k); keep.push(p); } }
                    const removed = split(area.value).length - keep.length;
                    if (removed) setBox(area, keep.join(', '));
                }
                toast('Duplicates removed');
            }}),
            el('button', {class: 'pv-btn', type: 'button', text: '🔃 Swap', title: 'Swap the positive and negative prompts', onclick: () => {
                const p = box('positive').value;
                setBox(box('positive'), box('negative').value);
                setBox(box('negative'), p);
            }})), out);

        async function checkTags() {
            let words;
            try { words = await vocab(); } catch (e) { toast(e.message, true); return; }
            const known = new Set(words.map((v) => key(v.t)));
            const unknown = [...new Set(split(box('positive').value))].filter((p) => {
                if (p.startsWith('<') || p === 'BREAK' || p.startsWith('__')) return false;
                if (p.split(/\s+/).length > 4) return false; // a sentence, not a tag
                return !known.has(key(p));
            });
            const note = S.vocabDanbooru ? '' : ' (checked against your library only: Danbooru\'s tags come with a WD14 model, downloaded the first time Image → Prompt reads with WD14)';
            out.replaceChildren(unknown.length
                ? el('div', {}, el('span', {class: 'pv-hint', text: `${unknown.length} unknown${note}: `}),
                    ...unknown.map((u) => el('button', {class: 'pv-chip pv-unknown', type: 'button', title: 'Add to the library', text: u + ' ＋', onclick: () => addAnywhereDialog(u)})),
                    el('button', {class: 'pv-mini', type: 'button', text: '✕', onclick: () => out.replaceChildren()}))
                : el('div', {class: 'pv-hint', text: 'Every tag is known' + note + '.'}));
        }
    }

    // ------------------------------------------------------------------ start

    function start() {
        if (!$('#pv_library')) return false;
        editorTools();
        for (const which of ['positive', 'negative']) {
            const area = box(which);
            if (area && !area.dataset.pvMarks) {
                area.dataset.pvMarks = '1';
                area.addEventListener('input', () => { clearTimeout(start.t); start.t = setTimeout(refreshMarks, 150); });
                attachSuggest(area);
            }
        }
        webuiSuggest();
        watchGenerate();
        // the AI tools write the editor from Python, without an input event: follow the value
        let last = '';
        setInterval(() => {
            const p = box('positive'), n = box('negative');
            const now = (p ? p.value : '') + '\u0001' + (n ? n.value : '');
            if (now !== last) { last = now; refreshMarks(); }
            watchGenerate();
        }, 800);
        loadLibrary();
        reloadSaved();
        return true;
    }

    // the same suggestions in the txt2img and img2img prompts, when the settings ask for them and the
    // tag autocomplete extension is not there to do it already (two lists under one box would fight)
    function webuiSuggest() {
        if (!window.opts || !opts.pv_autocomplete_webui || typeof TAC_CFG !== 'undefined' || $('#autocompleteResults')) return;
        for (const id of ['txt2img_prompt', 'txt2img_neg_prompt', 'img2img_prompt', 'img2img_neg_prompt']) {
            attachSuggest($(`#${id} textarea`));
        }
    }

    window.promptVault = {reloadSaved, reloadLibrary: loadLibrary, split, key, dedupePrompt, attachSuggest};

    const boot = () => { if (!start()) setTimeout(boot, 500); };
    if (typeof onUiLoaded === 'function') onUiLoaded(boot);
    else document.addEventListener('DOMContentLoaded', () => setTimeout(boot, 1000));
})();
