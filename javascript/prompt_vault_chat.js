// Prompt Vault: the chat with the local model (Qwen, Gemma, Mistral, GLM…). One conversation, shown in two places at
// once: the Chat tab of Muse's card and the Chat window of the Vault tab. Conversations live in the WebUI (lib_vault/chat.py) until it stops,
// unless saved; this file only shows them and sends what you write.

(() => {
    'use strict';

    const API = '/prompt-vault/api';
    const LS = {
        get(key, fallback) { try { const v = localStorage.getItem('pv_chat_' + key); return v === null ? fallback : JSON.parse(v); } catch (e) { return fallback; } },
        set(key, value) { try { localStorage.setItem('pv_chat_' + key, JSON.stringify(value)); } catch (e) { /* private window */ } },
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
            else if (k === 'html') node.innerHTML = v;
            else node.setAttribute(k, v === true ? '' : v);
        }
        for (const c of children.flat()) if (c !== null && c !== undefined && c !== false) node.append(c);
        return node;
    };
    const root = () => ((window.gradio_config && window.gradio_config.root) || '').replace(/\/$/, '');

    async function call(path, body) {
        const opts = body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)};
        const res = await fetch(root() + API + path, opts);
        let data = null;
        try { data = await res.json(); } catch (e) { /* not json */ }
        if (!res.ok) throw new Error((data && data.error) || ('HTTP ' + res.status));
        return data;
    }

    function toast(message, bad) {
        const box = $('#pv_toast') || (document.querySelector('.gradio-container') || document.body).appendChild(el('div', {id: 'pv_toast'}));
        box.textContent = message;
        box.className = 'pv-show' + (bad ? ' pv-bad' : '');
        clearTimeout(toast.t);
        toast.t = setTimeout(() => { box.className = ''; }, bad ? 5000 : 2200);
    }

    // ------------------------------------------------------------------ state, shared by every place it is shown

    const C = {
        list: {chats: [], saved: [], system_default: ''},
        chat: null,                 // the conversation shown
        busy: false,                // an answer is coming
        stream: '',                 // the answer so far
        thinking: '',               // a thinking model's reasoning so far
        pending: null,              // what you just sent, until the server has it
        cut: -1,                    // while a message is edited or answered again: the messages before it are shown
        editing: null,              // {id, text}: your message being edited
        assisting: '',              // 'enhance' | 'write' while the model writes into the box
        undoDraft: null,            // the box before Enhance or Write for me
        draft: '',
        files: [],                  // [{kind, name, data, size}] waiting to be sent
        context: LS.get('context', 'none'),
        verify: LS.get('verify', false), // 🔎 draft, look it up, correct, then answer
        step: '',                   // what Verify is doing
        leftOut: 0,
        status: '',
        panel: '',                  // '' | 'system' | 'saved'
        mounts: new Set(),
        ready: false,
    };

    function paint() {
        for (const m of [...C.mounts]) {
            if (!m.isConnected) { C.mounts.delete(m); continue; }
            const list = m.querySelector('.pv-chat-log');
            const y = list ? list.scrollTop : 0;
            const atEnd = !list || list.scrollHeight - list.scrollTop - list.clientHeight < 40;
            const box = m.querySelector('.pv-chat-input');
            const focused = box && document.activeElement === box;
            const caret = focused ? box.selectionStart : null;
            m.replaceChildren(view(m));
            const again = m.querySelector('.pv-chat-log');
            if (again) again.scrollTop = atEnd ? again.scrollHeight : y;
            if (focused) {
                const b = m.querySelector('.pv-chat-input');
                b.focus();
                if (caret !== null) b.setSelectionRange(caret, caret);
            }
            const edit = m.querySelector('.pv-chat-edit-box');
            if (edit && C.editing && C.editing.focus && edit.offsetParent) {  // in the window you see, not the hidden one
                C.editing.focus = false;
                edit.focus();
                edit.setSelectionRange(edit.value.length, edit.value.length);
            }
        }
    }

    // while the answer streams in, only its bubble changes
    let streamFrame = 0;
    function paintStream() {
        if (streamFrame) return;
        streamFrame = requestAnimationFrame(() => {
            streamFrame = 0;
            for (const m of C.mounts) {
                const th = m.querySelector('.pv-chat-streaming .pv-chat-thought-text');
                if (th && C.thinking) { th.textContent = C.thinking; th.parentElement.hidden = false; th.scrollTop = th.scrollHeight; }
                const t = m.querySelector('.pv-chat-streaming .pv-chat-text');
                if (!t) continue;
                const list = m.querySelector('.pv-chat-log');
                const atEnd = list.scrollHeight - list.scrollTop - list.clientHeight < 60;
                t.innerHTML = C.stream ? md(C.stream) + '<span class="pv-chat-caret"></span>'
                    : `<span class="pv-chat-wait">${esc(C.step || (C.thinking ? 'thinking…' : 'reading…'))}</span>`;
                if (atEnd) list.scrollTop = list.scrollHeight;
            }
        });
    }

    // ------------------------------------------------------------------ talking to the server

    async function refresh() {
        try { C.list = await call('/chat'); } catch (e) { return; }
        if (!C.chat) {
            const id = LS.get('id', '');
            if (id && C.list.chats.some((c) => c.id === id)) await load(id, true);
        }
        C.ready = true;
        paint();
    }

    async function load(id, quiet) {
        try {
            C.chat = (await call('/chat/one?id=' + encodeURIComponent(id))).chat;
            LS.set('id', C.chat.id);
        } catch (e) {
            C.chat = null;
            if (!quiet) toast(e.message, true);
        }
        C.leftOut = 0;
        paint();
    }

    // ------------------------------------------------------------------ presets: how the assistant behaves

    // who answers: the family of the model in use (Qwen, Gemma, Mistral, GLM…)
    const who = () => (C.list && C.list.model_label) || 'Model';

    const presets = () => (C.list && C.list.presets) || {builtin: [], mine: [], default: ''};
    const presetOf = (id) => [...presets().builtin, ...presets().mine].find((p) => p.id === id) || null;
    const presetLabel = (p) => (p ? `${p.icon || '⭐'} ${p.name}` : '✎ Custom');

    // a preset for the conversation you are in (an empty one), or a new one with it
    async function usePreset(id) {
        const p = presetOf(id);
        if (!p || C.busy) return;
        if (C.chat && !C.chat.messages.length) await act('/chat/update', {id: C.chat.id, system: p.text, preset: p.id});
        else await newChat(p.id);
        toast(`${presetLabel(p)}: from the next message on`);
    }

    async function newChat(preset) {
        if (C.busy) return;
        C.chat = (await call('/chat/new', typeof preset === 'string' ? {preset} : {})).chat;
        LS.set('id', C.chat.id);
        C.panel = '';
        C.leftOut = 0;
        await refresh();
    }

    async function stream(path, body) {
        C.busy = true;
        C.stream = '';
        C.thinking = '';
        C.step = '';
        paint();
        let failed = '';
        try {
            const res = await fetch(root() + API + path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
            if (!res.ok) {
                let data = null;
                try { data = await res.json(); } catch (e) { /* not json */ }
                throw new Error((data && data.error) || ('HTTP ' + res.status));
            }
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            for (;;) {
                const {value, done} = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, {stream: true});
                let nl;
                while ((nl = buffer.indexOf('\n')) >= 0) {
                    const line = buffer.slice(0, nl).trim();
                    buffer = buffer.slice(nl + 1);
                    if (!line) continue;
                    const ev = JSON.parse(line);
                    if (ev.start) { C.leftOut = ev.left_out || 0; paint(); }
                    if (ev.delta) { C.stream += ev.delta; paintStream(); }
                    if (ev.thinking) { C.thinking += ev.thinking; paintStream(); }
                    if (ev.step) { C.step = ev.step; paintStream(); }
                    if (ev.error) failed = ev.error;
                    if (ev.done && ev.status) C.status = ev.status;
                    if (ev.done && ev.chat) { C.chat = ev.chat; LS.set('id', ev.chat.id); }
                }
            }
        } catch (e) {
            failed = e.message;
        }
        C.busy = false;
        C.stream = '';
        C.thinking = '';
        C.step = '';
        if (failed) toast(failed, true);
        if (C.chat) await load(C.chat.id, true);
        await refresh();
        return !failed;
    }

    async function send() {
        if (C.busy) return;
        const text = C.draft.trim();
        if (!text && !C.files.length) return;
        if (!C.chat) await newChat();
        const files = C.files.map((f) => ({kind: f.kind, name: f.name, data: f.data}));
        C.pending = {role: 'user', text, files: C.files.map((f) => ({kind: f.kind, name: f.name, url: f.kind === 'image' ? f.data : ''}))};
        const keep = {draft: C.draft, files: C.files};
        C.undoDraft = null;
        C.draft = '';
        C.files = [];
        const ok = await stream('/chat/send', {id: C.chat.id, text, files, context: contextText(), verify: C.verify});
        if (!ok && C.pending) { C.draft = keep.draft; C.files = keep.files; }
        C.pending = null;
        paint();
    }

    const stop = () => { call('/chat/stop', {id: C.chat ? C.chat.id : 'assist'}).catch(() => {}); };

    // the box, as the model writes into it: every window's, without painting the rest again
    function paintDraft() {
        for (const m of C.mounts) {
            const box = m.querySelector('.pv-chat-input');
            if (box) { box.value = C.draft; box.scrollTop = box.scrollHeight; }
        }
    }

    // ✨ Enhance: the model rewrites your draft; ✍ Write for me: it writes your next message (your draft as its hint).
    // Nothing is sent: it lands in the box for you to read, change and send; ↩ Undo brings your words back.
    async function assist(mode) {
        if (C.busy) return;
        const before = C.draft;
        if (mode === 'enhance' && !before.trim()) { toast('Write a draft first: Enhance makes it better.', true); return; }
        C.busy = true;
        C.assisting = mode;
        C.undoDraft = before;
        C.draft = '';
        paint();
        let failed = '';
        let got = null;
        try {
            const res = await fetch(root() + API + '/chat/assist', {method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id: C.chat ? C.chat.id : '', mode, text: before, context: contextText()})});
            if (!res.ok) {
                let data = null;
                try { data = await res.json(); } catch (e) { /* not json */ }
                throw new Error((data && data.error) || ('HTTP ' + res.status));
            }
            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            for (;;) {
                const {value, done} = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, {stream: true});
                let nl;
                while ((nl = buffer.indexOf('\n')) >= 0) {
                    const line = buffer.slice(0, nl).trim();
                    buffer = buffer.slice(nl + 1);
                    if (!line) continue;
                    const ev = JSON.parse(line);
                    if (ev.delta) { C.draft += ev.delta; paintDraft(); }
                    if (ev.error) failed = ev.error;
                    if (ev.done) { got = ev.text; if (ev.banned_hits && ev.banned_hits.length) toast(`It used banned words anyway: ${ev.banned_hits.join(', ')}`, true); }
                }
            }
        } catch (e) {
            failed = e.message;
        }
        C.busy = false;
        C.assisting = '';
        if (got) C.draft = got;
        if (failed || !C.draft.trim()) {
            C.draft = before;
            C.undoDraft = null;
            if (failed) toast(failed, true);
        }
        paint();
        for (const m of C.mounts) {
            const box = m.querySelector('.pv-chat-input');
            if (box && box.offsetParent) { box.focus(); box.setSelectionRange(box.value.length, box.value.length); }
        }
    }

    const undoAssist = () => { if (C.undoDraft !== null) { C.draft = C.undoDraft; C.undoDraft = null; paint(); } };
    // a new answer to the message before this one; the earlier answer stays as a version (‹ 1/2 ›)
    async function again(m, at) {
        if (!C.chat || C.busy) return;
        C.editing = null;
        C.cut = at;
        await stream('/chat/regenerate', {id: C.chat.id, message: m.id, verify: C.verify});
        C.cut = -1;
        paint();
    }

    // your message with new words, answered anew; the earlier one stays as a version, with what followed it
    async function resend(m, at) {
        const text = ((C.editing && C.editing.text) || '').trim();
        if (!C.chat || C.busy || (!text && !(m.files || []).length)) return;
        C.editing = null;
        if (text === m.text.trim()) { paint(); return; }
        C.cut = at;
        C.pending = {role: 'user', text, files: m.files || []};
        await stream('/chat/edit', {id: C.chat.id, message: m.id, text, verify: C.verify});
        C.pending = null;
        C.cut = -1;
        paint();
    }

    const version = (m, step) => { if (!C.busy) act('/chat/version', {id: C.chat.id, message: m.id, step}); };
    // ⏪ back to one of your messages: all that came after it is gone (not kept as a version), and it is answered anew
    async function rewind(m, at) {
        if (!C.chat || C.busy) return;
        const after = C.chat.messages.length - at - 1;
        if (after && !confirm(`Rewind to here? The ${after} message${after > 1 ? 's' : ''} after it ${after > 1 ? 'are' : 'is'} removed for good, and it is answered anew.`)) return;
        C.editing = null;
        C.cut = at + 1;
        await stream('/chat/regenerate', {id: C.chat.id, rewind: m.id, verify: C.verify});
        C.cut = -1;
        paint();
    }

    // 🗜 the older part summed up and out of the model's memory; 📝 a wrap-up and a fresh conversation from it
    async function compactChat() {
        if (!C.chat || C.busy) return;
        if (await stream('/chat/compact', {id: C.chat.id})) toast(`Compacted: ${who()} keeps a summary of the earlier part`);
    }
    async function wrapUp() {
        if (!C.chat || C.busy) return;
        if (!confirm('Wrap up this conversation? A summary of it starts a new conversation with a clean memory; this one stays in the list.')) return;
        await stream('/chat/wrap', {id: C.chat.id});
    }

    const startEdit = (m) => { if (!C.busy) { C.editing = {id: m.id, text: m.text, focus: true}; paint(); } };

    async function act(path, body, then) {
        try {
            const data = await call(path, body);
            if (data.chat) C.chat = data.chat;
            if (then) then(data);
        } catch (e) { toast(e.message, true); }
        await refresh();
    }

    // ------------------------------------------------------------------ what the conversation can be given

    // the prompt you are working on, read with your message when you ask for it
    const CONTEXTS = [['none', 'No prompt'], ['muse', "Muse's idea"], ['vault', 'Vault editor'], ['txt2img', 'txt2img prompt']];
    function contextPrompt(kind) {
        if (kind === 'muse') return window.pvMuse && window.pvMuse.prompt ? window.pvMuse.prompt() : '';
        if (kind === 'vault') { const a = $('#pv_positive textarea'); return a ? a.value : ''; }
        if (kind === 'txt2img') { const a = $('#txt2img_prompt textarea'); return a ? a.value : ''; }
        return '';
    }
    function contextText() {
        const p = contextPrompt(C.context).trim();
        if (!p) return '';
        const where = (CONTEXTS.find((c) => c[0] === C.context) || [0, ''])[1];
        return `The image prompt I am working on (${where}):\n${p}`;
    }

    const TEXT_EXT = /\.(txt|md|markdown|json|csv|log|yaml|yml)$/i;
    async function addFiles(list) {
        for (const file of [...list]) {
            if (C.files.length >= 8) { toast('Eight files at most on one message', true); break; }
            if (file.type.startsWith('image/')) {
                if (file.size > 20 * 1024 * 1024) { toast(`${file.name}: too big (20 MB at most)`, true); continue; }
                const data = await new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = no; r.readAsDataURL(file); });
                C.files.push({kind: 'image', name: file.name || 'pasted image.png', data, size: file.size});
            } else if (file.type === 'application/pdf' || /\.pdf$/i.test(file.name)) {
                if (file.size > 40 * 1024 * 1024) { toast(`${file.name}: too big (40 MB at most)`, true); continue; }
                const data = await new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = no; r.readAsDataURL(file); });
                C.files.push({kind: 'pdf', name: file.name, data, size: file.size});
            } else if (file.type.startsWith('text/') || file.type === 'application/json' || TEXT_EXT.test(file.name)) {
                if (file.size > 2 * 1024 * 1024) { toast(`${file.name}: too big (2 MB at most)`, true); continue; }
                C.files.push({kind: 'text', name: file.name, data: await file.text(), size: file.size});
            } else {
                toast(`${file.name}: images (png, jpeg, webp), PDF, JSON, text and Markdown files only`, true);
            }
        }
        paint();
    }

    // ------------------------------------------------------------------ an answer, put to use

    // adults only, the same words Muse keeps out of every idea
    const MINOR = /\b(child|children|kid|kids|loli|lolicon|shota|shotacon|underage|minor|teen|teenager|preteen|toddler|infant|schoolgirl|schoolboy|cub|young girl|young boy|little girl|little boy|chibi)\b/gi;
    function promptOf(text) {
        const block = /```[\w-]*\n?([\s\S]*?)```/.exec(text || '');
        let p = (block ? block[1] : text || '').trim();
        p = p.replace(/^\s*(positive( prompt)?|prompt)\s*:\s*/i, '');
        const cleaned = p.replace(MINOR, '').replace(/\s*,\s*(,\s*)+/g, ', ').replace(/^[\s,]+|[\s,]+$/g, '');
        promptOf.note = cleaned !== p ? 'minor-related words left out' : '';
        // a tag with a banned word or phrase in it stays out of the prompt
        const ban = bannedWords().map((w) => new RegExp('(^|[^\\p{L}\\p{N}])' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '($|[^\\p{L}\\p{N}])', 'iu'));
        if (!ban.length) return cleaned;
        const tags = cleaned.split(/\s*,\s*/);
        const kept = tags.filter((t) => !ban.some((re) => re.test(t)));
        const out = tags.length - kept.length;
        if (out) promptOf.note = [promptOf.note, `${out} banned tag${out > 1 ? 's' : ''} left out`].filter(Boolean).join(', ');
        return kept.join(', ');
    }
    function write(area, value) {
        if (!area) return false;
        area.value = value;
        if (typeof updateInput === 'function') updateInput(area);
        else area.dispatchEvent(new Event('input', {bubbles: true}));
        return true;
    }
    const bannedWords = () => String((C.list && C.list.banned) || '').split(/[\n,;]+/).map((w) => w.trim()).filter(Boolean);

    function useAnswer(m, where) {
        const p = promptOf(m.text);
        if (!p) return;
        const note = promptOf.note && where !== 'copy' ? ` (${promptOf.note})` : '';
        if (where === 'copy') {
            navigator.clipboard.writeText(m.text).then(() => toast('Copied'), () => toast('The clipboard is blocked here', true));
        } else if (where === 'vault') {
            if (write($('#pv_positive textarea'), p)) toast('In the Vault editor' + note);
        } else if (where === 'txt2img' || where === 'img2img') {
            if (write($(`#${where}_prompt textarea`), p)) {
                toast('In ' + where + note);
                const go = window['switch_to_' + where];
                if (typeof go === 'function') { try { go(); } catch (e) { /* a nicety */ } }
            }
        } else if (where === 'muse' && window.pvMuse && window.pvMuse.setOwn) {
            window.pvMuse.setOwn(p).then(() => toast("Muse's Your prompt: Build around it with Enter there" + note));
        }
    }

    // ------------------------------------------------------------------ Markdown, a safe little of it

    const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    function inline(s) {
        return esc(s)
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>');
    }
    function md(src) {
        const out = [];
        const parts = String(src || '').split(/```/);
        parts.forEach((part, i) => {
            if (i % 2) {  // a code block
                const body = part.replace(/^[\w-]*\n/, '');
                out.push(`<pre class="pv-chat-code"><code>${esc(body.replace(/\n$/, ''))}</code></pre>`);
                return;
            }
            let list = '';
            const close = () => { if (list) { out.push(`</${list}>`); list = ''; } };
            for (const line of part.split('\n')) {
                const h = /^(#{1,4})\s+(.*)$/.exec(line);
                const ul = /^\s*[-*•]\s+(.*)$/.exec(line);
                const ol = /^\s*\d+[.)]\s+(.*)$/.exec(line);
                if (h) { close(); out.push(`<div class="pv-chat-h">${inline(h[2])}</div>`); }
                else if (ul) { if (list !== 'ul') { close(); out.push('<ul>'); list = 'ul'; } out.push(`<li>${inline(ul[1])}</li>`); }
                else if (ol) { if (list !== 'ol') { close(); out.push('<ol>'); list = 'ol'; } out.push(`<li>${inline(ol[1])}</li>`); }
                else if (!line.trim()) { close(); out.push('<div class="pv-chat-gap"></div>'); }
                else { close(); out.push(`<div>${inline(line)}</div>`); }
            }
            close();
        });
        return out.join('');
    }

    // ------------------------------------------------------------------ drawing

    function button(text, title, onclick, extra) {
        return el('button', Object.assign({type: 'button', class: 'pv-chat-btn', text, title, onclick}, extra || {}));
    }

    function files(list, removable) {
        if (!list || !list.length) return null;
        return el('div', {class: 'pv-chat-files'}, list.map((f, i) => el('span', {class: 'pv-chat-file', title: f.name},
            f.kind === 'image' && (f.url || f.data) ? el('img', {src: f.url || f.data, alt: f.name}) : el('span', {class: 'pv-chat-file-icon', text: f.kind === 'pdf' || f.pdf || /\.pdf/i.test(f.name) ? '📕' : /\.json$/i.test(f.name) ? '🧾' : '📄'}),
            el('span', {class: 'pv-chat-file-name', text: f.name}),
            removable ? el('button', {type: 'button', class: 'pv-chat-file-x', title: 'Remove', text: '✕',
                onclick: () => { C.files.splice(i, 1); paint(); }}) : null)));
    }

    // [2] in a checked answer: a link to that source
    function cite(htmlText, v) {
        const sources = (v && v.sources) || [];
        if (!sources.length) return htmlText;
        return htmlText.replace(/\[(\d{1,2})\](?![^<]*<\/code>)/g, (all, n) => {
            const x = sources[Number(n) - 1];
            return x ? `<a class="pv-chat-cite" href="${esc(x.url).replace(/"/g, '&quot;')}" target="_blank" rel="noopener noreferrer" title="${esc(x.title).replace(/"/g, '&quot;')}">[${n}]</a>` : all;
        });
    }

    // 🔎 what Verify did before the answer: what it looked up, what it found, the tags it fixed, the first draft
    function checkedView(v) {
        const sources = v.sources || [];
        const tags = v.tags || [];
        const label = [sources.length ? `${sources.length} source${sources.length > 1 ? 's' : ''}` : 'nothing found',
            tags.length ? `${tags.length} tag${tags.length > 1 ? 's' : ''} fixed` : '', (v.problems || []).length ? 'with problems' : '']
            .filter(Boolean).join(' · ');
        return el('details', {class: 'pv-chat-thought pv-chat-checked'},
            el('summary', {text: `🔎 Checked: ${label}`}),
            (v.queries || []).length || (v.models || []).length
                ? el('div', {class: 'pv-chat-meta', text: 'Looked up: ' + (v.queries || []).concat((v.models || []).map((x) => x + ' (Civitai)')).join(' · ')})
                : el('div', {class: 'pv-chat-meta', text: 'Nothing in the draft needed looking up'}),
            sources.length ? el('ol', {class: 'pv-chat-sources'}, sources.map((x) => el('li', {title: x.read ? 'read: the parts of this page on the question' : 'the search snippet only'},
                el('a', {href: x.url, target: '_blank', rel: 'noopener noreferrer', text: (x.read ? '📖 ' : '') + (x.title || x.url)})))) : null,
            tags.length ? el('div', {class: 'pv-chat-meta', text: 'Not Danbooru tags: ' + tags.map((t) => t.tag + (t.suggest && t.suggest.length ? ` → ${t.suggest.join(' / ')}` : '')).join('; ')}) : null,
            (v.problems || []).length ? el('div', {class: 'pv-chat-meta pv-chat-banned-hit', text: 'Could not: ' + v.problems.join('; ')}) : null,
            v.draft ? el('details', {class: 'pv-chat-draft'}, el('summary', {text: 'The first draft'}), el('div', {class: 'pv-chat-thought-text', text: v.draft})) : null);
    }

    // ‹ 2/3 ›: the versions of a message, each with what followed it
    function versions(m) {
        if (!m.versions || m.versions < 2) return null;
        return el('span', {class: 'pv-chat-versions'},
            button('‹', 'The earlier version', () => version(m, -1), {disabled: C.busy || m.version <= 1}),
            el('span', {class: 'pv-chat-meta', text: `${m.version}/${m.versions}`}),
            button('›', 'The later version', () => version(m, 1), {disabled: C.busy || m.version >= m.versions}));
    }

    function editor(m, at) {
        const box = el('textarea', {class: 'pv-chat-edit-box', rows: '3', spellcheck: 'true'});
        box.value = C.editing.text;
        box.addEventListener('input', () => { C.editing.text = box.value; });
        box.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); resend(m, at); }
            if (e.key === 'Escape') { e.stopPropagation(); C.editing = null; paint(); }
        });
        return el('div', {class: 'pv-chat-msg pv-chat-mine pv-chat-editing'},
            el('div', {class: 'pv-chat-who', text: 'You · editing'}),
            files(m.files),
            box,
            el('div', {class: 'pv-chat-actions'},
                el('span', {class: 'pv-chat-meta', text: `${who()} answers it anew; the earlier version is kept`}),
                button('Cancel', 'Keep it as it was (Esc)', () => { C.editing = null; paint(); }),
                button('Send', 'Send the new words (Enter)', () => resend(m, at), {class: 'pv-chat-btn pv-chat-send'})));
    }

    function bubble(m, last, at) {
        const mine = m.role === 'user';
        if (mine && C.editing && C.editing.id === m.id && !C.busy) return editor(m, at);
        const actions = mine
            ? el('div', {class: 'pv-chat-actions'},
                versions(m),
                C.busy || !m.id ? null : button('✎ Edit', 'Change these words; it is answered anew and the earlier version is kept (or double-click the message)', () => startEdit(m)),
                C.busy || !m.id ? null : button('⏪', 'Rewind to here: everything after this message is removed, and it is answered anew', () => rewind(m, at)),
                C.busy || !m.id ? null : button('✕', 'Remove this message', () => act('/chat/remove-message', {id: C.chat.id, message: m.id})))
            : el('div', {class: 'pv-chat-actions'},
                versions(m),
                button('Copy', 'Copy the answer', () => useAnswer(m, 'copy')),
                button('→ Vault', 'The prompt in it (its code block, or all of it) into the Vault editor', () => useAnswer(m, 'vault')),
                button('→ txt2img', 'The prompt in it into txt2img', () => useAnswer(m, 'txt2img')),
                button('→ Muse', "The prompt in it as Muse's Your prompt", () => useAnswer(m, 'muse')),
                !C.busy && m.id ? button('↻ Again', 'A new answer; this one is kept as a version (‹ ›)', () => again(m, at)) : null,
                m.stopped ? el('span', {class: 'pv-chat-meta', text: 'stopped'}) : null,
                m.banned_hits && m.banned_hits.length ? el('span', {class: 'pv-chat-meta pv-chat-banned-hit', title: 'Banned words it used anyway (a phrase can only be asked to be avoided): ↻ Again for another answer',
                    text: `⚠ ${m.banned_hits.join(', ')}`}) : null,
                m.seconds ? el('span', {class: 'pv-chat-meta', text: `${m.seconds}s`}) : null);
        return el('div', {class: 'pv-chat-msg ' + (mine ? 'pv-chat-mine' : 'pv-chat-theirs')},
            el('div', {class: 'pv-chat-who', text: mine ? 'You' : who()}),
            files(m.files),
            m.verify ? checkedView(m.verify) : null,
            m.thinking ? el('details', {class: 'pv-chat-thought'},
                el('summary', {text: `💭 Thought (${m.thinking.split(/\s+/).length} words)`}),
                el('div', {class: 'pv-chat-thought-text', text: m.thinking})) : null,
            m.text ? el('div', {class: 'pv-chat-text', html: mine ? esc(m.text).replace(/\n/g, '<br>') : cite(md(m.text), m.verify),
                ondblclick: mine && m.id ? () => startEdit(m) : null}) : null,
            actions);
    }

    function head() {
        const c = C.chat;
        const pick = el('select', {class: 'pv-chat-pick', title: 'Conversations of this session', onchange: (e) => {
            const v = e.target.value;
            if (v === '__new') newChat();
            else if (v) load(v);
        }},
        el('option', {value: '', text: c ? '' : 'No conversation yet', disabled: true, selected: !c}),
        ...C.list.chats.map((x) => el('option', {value: x.id, text: (x.saved_as ? '💾 ' : '') + x.title, selected: c && x.id === c.id})),
        el('option', {value: '__new', text: '＋ New conversation'}));
        return el('div', {class: 'pv-chat-head'}, pick,
            button('＋', 'New conversation', newChat, {disabled: C.busy}),
            button('⚙ Muse', 'Open Muse settings: the model, vision, memory, sampling', () => {
                if (window.pvMuse && window.pvMuse.openSettings) window.pvMuse.openSettings();
                else toast('Muse is not loaded', true);
            }, {class: 'pv-chat-btn pv-chat-to-muse'}),
            c ? button(c.saved_as ? '💾 Saved' : '💾 Save', c.saved_as ? `Kept in prompt_vault/chats/${c.saved_as}, and as it goes on. Click: not kept any more`
                : 'Keep it: saved in prompt_vault/chats/ (otherwise it is gone when the WebUI stops)',
            () => act(c.saved_as ? '/chat/unsave' : '/chat/save', {id: c.id}, () => toast(c.saved_as ? 'Not kept any more' : 'Saved')),
            {class: 'pv-chat-btn' + (c.saved_as ? ' pv-on' : '')}) : null,
            button('📂', 'Saved conversations; import a JSON one', () => { C.panel = C.panel === 'saved' ? '' : 'saved'; paint(); },
                {class: 'pv-chat-btn' + (C.panel === 'saved' ? ' pv-on' : '')}),
            c ? button('⚙ ' + ((presetOf(c.preset) || {}).icon || '✎'), `How the assistant behaves here: ${presetLabel(presetOf(c.preset))}. Presets and the system prompt`,
                () => { C.panel = C.panel === 'system' ? '' : 'system'; paint(); },
                {class: 'pv-chat-btn' + (C.panel === 'system' ? ' pv-on' : '')}) : null,
            c ? button('⇩ .md', 'Export as Markdown', () => exportChat('md')) : null,
            c ? button('⇩ .json', 'Export as JSON (can be imported again)', () => exportChat('json')) : null,
            c ? button('🗑', 'Close this conversation (a saved copy stays saved)', () => {
                if (!confirm('Close this conversation? Unless it is saved, it is gone.')) return;
                act('/chat/delete', {id: c.id}, () => { C.chat = null; LS.set('id', ''); });
            }, {disabled: C.busy}) : null);
    }

    async function exportChat(fmt) {
        try {
            const data = await call(`/chat/export?id=${encodeURIComponent(C.chat.id)}&fmt=${fmt}`);
            const url = URL.createObjectURL(new Blob([data.text], {type: data.type}));
            el('a', {href: url, download: data.name}).click();
            setTimeout(() => URL.revokeObjectURL(url), 5000);
        } catch (e) { toast(e.message, true); }
    }

    // 🚫 words the model must not write, in every conversation
    function bannedView() {
        const box = el('textarea', {class: 'pv-chat-system pv-chat-banned', rows: '3', spellcheck: 'false',
            placeholder: 'One word or phrase a line, or comma-separated: tapestry, testament, shivers down her spine…'});
        box.value = (C.list && C.list.banned) || '';
        const count = el('span', {class: 'pv-chat-meta', text: `${bannedWords().length} banned`});
        return el('div', {class: 'pv-chat-banned-box'},
            el('div', {class: 'pv-chat-label', text: '🚫 Banned words (every conversation)'}),
            box,
            el('div', {class: 'pv-chat-row'},
                button('Keep', 'Use these from the next answer on', () => act('/chat/banned', {text: box.value}, (d) => toast(`${d.words.length} banned words`)),
                    {class: 'pv-chat-btn pv-chat-send'}),
                button('＋ Common clichés', 'Add the words and phrases AI writing leans on (tapestry, testament, delve…)', () => {
                    const have = new Set(box.value.split(/[\n,;]+/).map((w) => w.trim().toLowerCase()).filter(Boolean));
                    const more = String((C.list && C.list.cliches) || '').split(/\s*,\s*/).filter((w) => w && !have.has(w.toLowerCase()));
                    box.value = [box.value.trim(), more.join(', ')].filter(Boolean).join(box.value.trim() ? ',\n' : '');
                }),
                count),
            el('div', {class: 'pv-chat-hint', text: 'A single word is blocked while the model writes; a phrase, or another form of a word, is asked to be avoided, '
                + 'and ⚠ marks an answer that used one anyway. Tags with a banned word stay out of what → Vault, → txt2img and → Muse send.'}));
    }

    function panelView() {
        if (C.panel === 'system' && C.chat) {
            const pr = presets();
            let chosen = C.chat.preset || '';
            const box = el('textarea', {class: 'pv-chat-system', rows: '6', spellcheck: 'false'});
            box.value = C.chat.system || '';
            const hint = el('div', {class: 'pv-chat-hint', text: (presetOf(chosen) || {}).hint || ''});
            const opt = (p) => el('option', {value: p.id, text: presetLabel(p) + (p.id === pr.default ? '  ★' : ''), selected: p.id === chosen});
            const pick = el('select', {class: 'pv-chat-preset', title: 'A preset fills the system prompt; you can still change it below', onchange: (e) => {
                const p = presetOf(e.target.value);
                if (!p) return;
                chosen = p.id;
                box.value = p.text;
                hint.textContent = p.hint || '';
            }},
            !chosen ? el('option', {value: '', text: '✎ Custom (written by hand)', selected: true}) : null,
            el('optgroup', {label: 'Built in'}, pr.builtin.map(opt)),
            pr.mine.length ? el('optgroup', {label: 'My presets'}, pr.mine.map(opt)) : null);
            const edited = () => { const p = presetOf(chosen); return !p || p.text.trim() !== box.value.trim(); };
            return el('div', {class: 'pv-chat-panel'},
                el('div', {class: 'pv-chat-row'}, el('span', {class: 'pv-chat-label', text: 'Preset'}), pick),
                hint, box,
                el('div', {class: 'pv-chat-row'},
                    button('Use', 'This system prompt, from the next message on', () => act('/chat/update', {id: C.chat.id, system: box.value, preset: chosen},
                        () => { C.panel = ''; toast('System prompt in use'); }), {class: 'pv-chat-btn pv-chat-send'}),
                    button('💾 Save as preset', 'Keep this system prompt as a preset of yours (same name: replaced)', async () => {
                        const p = presetOf(chosen);
                        const name = prompt('Name of your preset:', p && !pr.builtin.includes(p) ? p.name : '');
                        if (!name) return;
                        await act('/chat/presets/save', {name, text: box.value}, async (d) => {
                            await act('/chat/update', {id: C.chat.id, system: box.value, preset: d.saved});
                            toast(`Saved: ${name}`);
                        });
                    }),
                    button('★ Default', 'New conversations start with this preset', () => {
                        if (edited()) { toast('Save it as a preset first: ★ makes a preset the default', true); return; }
                        act('/chat/presets/default', {id: chosen}, () => toast(`New conversations: ${presetLabel(presetOf(chosen))}`));
                    }),
                    pr.mine.some((p) => p.id === chosen) ? button('🗑', 'Delete this preset of yours', () => {
                        if (confirm(`Delete the preset ${presetOf(chosen).name}?`)) act('/chat/presets/delete', {id: chosen});
                    }) : null),
                el('div', {class: 'pv-chat-hint', text: 'The model decides what it will write; a model that refuses needs another model, not another prompt.'}),
                bannedView());
        }
        if (C.panel === 'saved') {
            const imp = el('input', {type: 'file', accept: '.json,application/json', class: 'pv-chat-hidden', onchange: async (e) => {
                const f = e.target.files[0];
                if (!f) return;
                try { await act('/chat/import', {data: JSON.parse(await f.text())}, (d) => { LS.set('id', d.chat.id); C.panel = ''; toast('Imported'); }); }
                catch (err) { toast('Not a conversation exported from here', true); }
            }});
            return el('div', {class: 'pv-chat-panel'},
                el('div', {class: 'pv-chat-label', text: C.list.saved.length ? 'Saved conversations' : 'No saved conversation yet: 💾 Save keeps the one you are in'}),
                el('div', {class: 'pv-chat-saved'}, C.list.saved.map((s) => el('div', {class: 'pv-chat-saved-row'},
                    el('button', {type: 'button', class: 'pv-chat-saved-open', title: s.name, onclick: () => act('/chat/open', {name: s.name}, (d) => { LS.set('id', d.chat.id); C.panel = ''; })},
                        el('span', {text: s.title}), el('span', {class: 'pv-chat-meta', text: `${s.count} messages · ${new Date(s.updated * 1000).toLocaleString()}`})),
                    button('🗑', 'Delete the saved file', () => { if (confirm(`Delete ${s.title}?`)) act('/chat/saved/delete', {name: s.name}); })))),
                el('div', {class: 'pv-chat-row'}, imp, button('⇧ Import .json', 'A conversation exported as JSON', () => imp.click())));
        }
        return null;
    }

    const EMOJI = {
        'Faces': '😀😁😂🤣😃😄😅😆😉😊😋😎😍😘🥰😗😙😚🙂🤗🤩🤔🤨😐😑😶🙄😏😣😥😮🤐😯😪😫🥱😴😌😛😜😝🤤😒😓😔😕🙃🤑😲☹️🙁😖😞😟😤😢😭😦😧😨😩🤯😬😰😱🥵🥶😳🤪😵🥴😠😡🤬😷🤒🤕🤢🤮🤧😇🥳🥺🤠🤡🤥🤫🤭🧐🤓😈👿💀☠️👻👽🤖💩',
        'Hands': '👍👎👏🙌👐🤲🤝🤞✌️🤟🤘👌🤌🤏👈👉👆👇☝️👋🤚🖐️✋🖖👊✊🤛🤜💪🙏',
        'Hearts': '❤️🧡💛💚💙💜🖤🤍🤎💔❣️💕💞💓💗💖💘💝💋😻',
        'Marks': '✨🔥⭐🌟💫⚡💥💯✅❌⚠️❗❓‼️⁉️💡📌📍🎯🎉🎊🎁🏆🥇🎵🎶🔔💬💭💤🌀🆗🆕🆙🆒',
        'Nature': '☀️🌤️⛅🌥️☁️🌦️🌧️⛈️🌩️🌨️❄️☃️🌬️💨🌈🌙⭐🌸🌺🌻🌹🌷🍀🍁🍂🍃🌿🌱🌵🌴🌳🌲',
        'Animals': '🐱🐶🐭🐹🐰🦊🐻🐼🐨🐯🦁🐮🐷🐸🐵🙈🙉🙊🐔🐧🐦🐤🦆🦅🦉🦇🐺🐗🐴🦄🐝🐛🦋🐌🐞',
        'Food': '🍎🍊🍋🍌🍉🍇🍓🫐🍒🍑🥭🍍🥝🍅🥑🥦🥕🌽🍞🧀🍖🍗🍔🍟🍕🌭🌮🍣🍪🍩🍰☕🍵🍺',
        'Objects': '📷🎨🖌️✏️📝📚🔖📎📁💻📱⌨️🖱️🎮🎲🧩🔮💎💍👑🎀👓🕶️⌚⏰🔑🔒🧲💊💉',
    };

    function insertAt(box, text) {
        const a = box.selectionStart == null ? box.value.length : box.selectionStart;
        const b = box.selectionEnd == null ? a : box.selectionEnd;
        box.value = box.value.slice(0, a) + text + box.value.slice(b);
        const at = a + text.length;
        box.setSelectionRange(at, at);
        C.draft = box.value;
        box.focus();
    }

    function emojiButton(box) {
        let pop = null;
        const wrap = el('span', {class: 'pv-emoji-wrap pv-chat-emoji-wrap'});
        const btn = button('😊', 'Insert an emoji, or ask the model for one', () => {
            if (pop) { pop.remove(); pop = null; return; }
            const made = el('div', {class: 'pv-emoji-grid'});
            const hint = el('input', {type: 'text', placeholder: 'sad cat, rain, fire…', spellcheck: 'false'});
            const chars = (s) => (typeof Intl !== 'undefined' && Intl.Segmenter)
                ? [...new Intl.Segmenter().segment(s)].map((x) => x.segment)
                : [...s];
            const scroll = el('div', {class: 'pv-emoji-scroll'}, Object.entries(EMOJI).map(([name, set]) => el('div', {},
                el('div', {class: 'pv-emoji-label', text: name}),
                el('div', {class: 'pv-emoji-grid'}, chars(set).map((ch) => button(ch, ch, () => insertAt(box, ch)))))));
            const make = button('Make', 'Ask the model for emoji that match this', async () => {
                const text = hint.value.trim();
                if (!text) { hint.focus(); return; }
                make.disabled = true;
                try {
                    const data = await call('/chat/emoji', {hint: text});
                    made.replaceChildren(...(data.emoji || []).map((ch) => button(ch, ch, () => insertAt(box, ch))));
                    if (!data.emoji || !data.emoji.length) toast('No emoji came back', true);
                } catch (e) { toast(e.message, true); }
                make.disabled = false;
            });
            pop = el('div', {class: 'pv-emoji-pop'},
                scroll, el('div', {class: 'pv-emoji-make'}, hint, make), made);
            wrap.append(pop);
            hint.focus();
        });
        wrap.append(btn);
        return wrap;
    }

    function composer() {
        const box = el('textarea', {class: 'pv-chat-input', rows: '2', spellcheck: 'true',
            placeholder: `Write to ${who()}… Enter sends, Shift+Enter a new line. Add ${C.list && C.list.vision === false ? '' : 'images or '}.txt/.md with 📎, paste or drop them.`});
        box.value = C.draft;
        if (C.assisting) box.readOnly = true;
        box.addEventListener('input', () => { C.draft = box.value; });
        box.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); C.draft = box.value; send(); }
        });
        box.addEventListener('paste', (e) => {
            const got = [...(e.clipboardData ? e.clipboardData.files : [])];
            if (got.length) { e.preventDefault(); addFiles(got); }
        });
        const pickFile = el('input', {type: 'file', multiple: true, class: 'pv-chat-hidden',
            accept: 'image/png,image/jpeg,image/webp,.txt,.md,.markdown,.json,.csv,.pdf,text/plain,text/markdown,application/json,application/pdf',
            onchange: (e) => addFiles(e.target.files)});
        const emoji = emojiButton(box);
        const ctx = el('select', {class: 'pv-chat-ctx', title: 'Read with your message: the prompt you are working on', onchange: (e) => { C.context = e.target.value; LS.set('context', C.context); }},
            CONTEXTS.map(([v, t]) => el('option', {value: v, text: '+ ' + t, selected: v === C.context})));
        const helper = el('div', {class: 'pv-chat-assist'},
            C.assisting ? el('span', {class: 'pv-chat-wait', text: C.assisting === 'enhance' ? `${who()} is improving your draft…` : `${who()} is writing for you…`})
                : [button('✨ Enhance my draft', 'The model rewrites what you wrote: clearer, more specific, in your words and language. Not sent: read it, change it, send it',
                    () => { C.draft = box.value; assist('enhance'); }, {disabled: C.busy}),
                   button('✍ Write for me', 'The model writes your next message from the conversation (what is in the box is its hint). Not sent',
                    () => { C.draft = box.value; assist('write'); }, {disabled: C.busy}),
                   C.undoDraft !== null && !C.busy ? button('↩ Undo', 'Back to what you had written', undoAssist) : null,
                   el('span', {class: 'pv-chat-grow'}),
                   button(C.verify ? '🔎 Verify: on' : '🔎 Verify', C.verify ? 'On: the model drafts, looks the draft up on the web (and its tags on Danbooru), corrects it, then answers. Slower. Click: off'
                    : 'Off. On: the model drafts, looks the draft up on the web (and its tags on Danbooru), corrects it, then answers',
                    () => { C.verify = !C.verify; LS.set('verify', C.verify); paint(); }, {class: 'pv-chat-btn pv-chat-verify' + (C.verify ? ' pv-on' : '')})]);
        return el('div', {class: 'pv-chat-compose'},
            files(C.files, true),
            helper,
            box,
            el('div', {class: 'pv-chat-row'},
                pickFile, button('📎', 'Add images (png, jpeg, webp), PDF, JSON, text or Markdown files', () => pickFile.click()),
                emoji,
                ctx,
                el('span', {class: 'pv-chat-grow'}),
                C.busy ? button('■ Stop', C.assisting ? 'Stop writing here' : 'Stop the answer here', stop, {class: 'pv-chat-btn pv-chat-stop'})
                    : button('Send', 'Send (Enter)', () => { C.draft = box.value; send(); }, {class: 'pv-chat-btn pv-chat-send'})));
    }

    // how full the model's context is: the conversation, of what it may take (the rest is kept for the answer)
    const kTok = (n) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(Math.round(n)));
    function contextMeter() {
        const x = C.chat && C.chat.context;
        if (!x || !C.chat.messages.length || !x.room) return null;
        const share = x.used / x.room;
        const level = share >= 1 ? 'pv-ctx-over' : share >= 0.75 ? 'pv-ctx-high' : '';
        const note = share >= 1 ? 'full: 🗜 Compact sums up the older part, 📝 Wrap up starts afresh from a summary'
            : share >= 0.75 ? 'nearly full: it compacts by itself at 90% (Settings), or 🗜 Compact now' : '';
        const canCompact = C.chat.messages.length >= 6 || share >= 0.5;
        const canWrap = C.chat.messages.length >= 4 || !!C.chat.summary;
        return el('div', {class: 'pv-chat-ctx-meter ' + level,
            title: `Context size ${x.size} tokens (Settings → Prompt Vault → Context size): ${x.reserve} kept for the answer, ` +
                `the rest for the conversation and its system prompt. Counts are estimates; an image is about its width × height / 1024.`},
            el('span', {class: 'pv-ctx-label', text: 'Context'}),
            el('span', {class: 'pv-ctx-bar'}, el('span', {class: 'pv-ctx-fill', style: `width:${Math.min(100, share * 100).toFixed(1)}%`})),
            el('span', {class: 'pv-ctx-num', text: `~${kTok(x.used)} / ${kTok(x.room)} tokens · ${Math.round(share * 100)}%`}),
            canCompact ? button('🗜 Compact', 'Sum up the older part of the conversation and take it out of the model\'s memory; the last messages stay as they are',
                compactChat, {class: 'pv-chat-btn pv-ctx-tool', disabled: C.busy}) : null,
            canWrap ? button('📝 Wrap up', 'Write up what the conversation came to, and start a new one, with a clean memory, from that summary',
                wrapUp, {class: 'pv-chat-btn pv-ctx-tool', disabled: C.busy}) : null,
            note ? el('span', {class: 'pv-ctx-note', text: note}) : null);
    }

    function view(m) {
        const c = C.chat;
        const msgs = c ? c.messages.slice(0, C.cut >= 0 ? C.cut : undefined) : [];
        if (C.pending) msgs.push(C.pending);
        const log = el('div', {class: 'pv-chat-log'},
            !msgs.length && !C.busy ? el('div', {class: 'pv-chat-empty'},
                el('strong', {text: C.list && C.list.model_name ? `Chat · ${C.list.model_name}` : 'Chat'}),
                el('div', {text: `Talk with the local model (${who()}): ideas, prompts, ${C.list && C.list.vision === false ? '' : 'a picture to describe, '}a story to turn into prompts. Choose the model in Muse → ⚙.`}),
                el('div', {text: 'This conversation lasts until the WebUI stops; 💾 Save keeps it. It is the same one here and in the Vault tab.'}),
                presets().builtin.length ? el('div', {class: 'pv-chat-presets'},
                    el('div', {class: 'pv-chat-label', text: 'Start as'}),
                    el('div', {class: 'pv-chat-preset-chips'}, [...presets().builtin, ...presets().mine].map((p) =>
                        el('button', {type: 'button', class: 'pv-chat-chip' + (c && c.preset === p.id ? ' pv-on' : ''), title: p.hint || p.text.slice(0, 200),
                            text: presetLabel(p), onclick: () => usePreset(p.id)})))) : null) : null,
            c && (c.summary || (c.archived || []).length) ? el('details', {class: 'pv-chat-thought pv-chat-compacted'},
                el('summary', {text: `🗜 ${(c.archived || []).length} earlier message${(c.archived || []).length === 1 ? '' : 's'} compacted: what ${who()} keeps of them`}),
                el('div', {class: 'pv-chat-thought-text', text: c.summary || ''}),
                (c.archived || []).length ? el('details', {class: 'pv-chat-draft'}, el('summary', {text: 'The messages themselves (no longer read)'}),
                    c.archived.map((m) => el('div', {class: 'pv-chat-archived'}, el('strong', {text: m.role === 'user' ? 'You: ' : `${who()}: `}), m.text))) : null) : null,
            msgs.map((x, i) => bubble(x, i === msgs.length - 1 && x.role === 'assistant', i)),
            C.busy && !C.assisting ? el('div', {class: 'pv-chat-msg pv-chat-theirs pv-chat-streaming'},
                el('div', {class: 'pv-chat-who', text: who()}),
                el('div', {class: 'pv-chat-thought pv-chat-thinking-now', hidden: !C.thinking},
                    el('div', {class: 'pv-chat-thought-head', text: '💭 Thinking'}),
                    el('div', {class: 'pv-chat-thought-text', text: C.thinking})),
                el('div', {class: 'pv-chat-text', html: C.stream ? md(C.stream) + '<span class="pv-chat-caret"></span>' : `<span class="pv-chat-wait">${esc(C.step || 'thinking…')}</span>`})) : null);
        const foot = [C.leftOut ? `${C.leftOut} older message${C.leftOut > 1 ? 's are' : ' is'} beyond the model's context: not read` : '', C.status ? `${who()}: ` + C.status : '']
            .filter(Boolean).join(' · ');
        const body = el('div', {class: 'pv-chat' + (m.dataset.compact ? ' pv-chat-compact' : '')},
            head(), panelView(), log, composer(), contextMeter(), foot ? el('div', {class: 'pv-chat-status', text: foot}) : null);
        body.addEventListener('dragover', (e) => { e.preventDefault(); body.classList.add('pv-chat-drop'); });
        body.addEventListener('dragleave', () => body.classList.remove('pv-chat-drop'));
        body.addEventListener('drop', (e) => { e.preventDefault(); body.classList.remove('pv-chat-drop'); if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files); });
        return body;
    }

    // ------------------------------------------------------------------ the places it is shown

    function mount(node, opts) {
        if (!node) return;
        if (opts && opts.compact) node.dataset.compact = '1';
        C.mounts.add(node);
        node.replaceChildren(view(node));
        const list = node.querySelector('.pv-chat-log');
        if (list) list.scrollTop = list.scrollHeight;
        if (!C.ready) refresh();
    }

    window.pvChat = {mount, refresh};

    // the window of the Vault tab
    const boot = () => {
        const host = $('#pv_chat_vault');
        if (!host) { setTimeout(boot, 800); return; }
        mount(host);
    };
    if (typeof onUiLoaded === 'function') onUiLoaded(boot);
    else document.addEventListener('DOMContentLoaded', () => setTimeout(boot, 1000));
})();
