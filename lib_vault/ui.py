"""The Prompt Vault tab.

Button emojis avoid the ones Lobe Theme swaps for icons (✨ 🪄 🖼️ 💾 ⬇️ 📋 🔄 ⇅ ...): it replaces
the whole label of any button that contains one.

Top to bottom: the editor (positive and negative), the AI tools (TIPO, Qwen,
Image -> Prompt), saved prompts and history, and the tag library. The library,
saved prompts and history are drawn by javascript/prompt_vault.js from the
routes in api.py; Gradio only holds the editor and the AI tools.
"""

from __future__ import annotations

import base64
import io

import gradio as gr

from . import VERSION, qwen, qwen_prompts, store, text, tipo, wd14
from . import llama

INTO = ["Replace", "Append"]
READ_WITH = ["WD14 tags", "Qwen tags", "Qwen description", "WD14 tags + Qwen description"]

JS_PULL = """
function(target, pos, neg) {
    const get = (id) => { const el = gradioApp().querySelector('#' + id + ' textarea'); return el ? el.value : null; };
    const p = get(target + '_prompt'), n = get(target + '_neg_prompt');
    return [target, p === null ? pos : p, n === null ? neg : n];
}
"""

JS_SEND = """
function(target, pos, neg) {
    const clean = (value) => (window.promptVault && promptVault.dedupePrompt) ? promptVault.dedupePrompt(value || '') : (value || '');
    const put = (id, value) => {
        const el = gradioApp().querySelector('#' + id + ' textarea');
        if (!el || !value.trim()) return;
        el.value = value;
        if (typeof updateInput === 'function') updateInput(el); else el.dispatchEvent(new Event('input', {bubbles: true}));
    };
    pos = clean(pos);
    neg = clean(neg);
    put(target + '_prompt', pos);
    put(target + '_neg_prompt', neg);
    return [target, pos, neg];
}
"""

JS_RELOAD_SAVED = "function(){ if (window.promptVault) window.promptVault.reloadSaved(); return []; }"


def _note(message):
    return f"<span class='pv-note'>{message}</span>" if message else ""


def _thumb(image):
    if image is None:
        return None
    try:
        im = image.convert("RGB")
        im.thumbnail((160, 160))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=80)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return None


def _generation_info(image):
    """The positive and negative prompt written into an image by the WebUI, or None."""
    if image is None:
        return None
    info = (getattr(image, "info", None) or {}).get("parameters")
    if not info:
        try:
            from modules import images

            info, _ = images.read_info_from_image(image)
        except Exception:
            info = None
    if not info:
        return None
    parse = None
    for path in ("modules.infotext_utils", "modules.generation_parameters_copypaste"):
        try:
            parse = __import__(path, fromlist=["parse_generation_parameters"]).parse_generation_parameters
            break
        except Exception:
            continue
    if parse is None:
        return None
    try:
        params = parse(info)
    except Exception:
        return None
    return params.get("Prompt", ""), params.get("Negative prompt", "")


def build():
    with gr.Blocks(analytics_enabled=False) as tab:
        # ============================================================ editor
        with gr.Group(elem_id="pv_editor"):
            positive = gr.Textbox(label="Positive", lines=4, elem_id="pv_positive",
                                  placeholder="Type, pick tags from the library below, or pull from txt2img")
            negative = gr.Textbox(label="Negative", lines=2, elem_id="pv_negative",
                                  placeholder="Negative prompt; tags of the Negative categories land here")
        gr.HTML("<div id='pv_editor_tools'></div>")
        with gr.Row(elem_id="pv_io_row", equal_height=True):
            target = gr.Radio(["txt2img", "img2img"], value="txt2img", label="Workspace", elem_id="pv_target",
                              scale=2)
            pull = gr.Button("📥 Pull from workspace", elem_id="pv_pull", scale=1)
            send = gr.Button("📤 Send to workspace", variant="primary", elem_id="pv_send", scale=1)
            clear = gr.Button("🧹 Clear", elem_id="pv_clear", scale=1)

        # ============================================================ TIPO
        with gr.Accordion("🌱 Expand with TIPO", open=False, elem_id="pv_tipo"):
            gr.Markdown("Turns a few tags or a short idea into a full prompt. Runs on this machine; the model "
                        "(0.4-2 GB) downloads on first use. Settings → **Prompt Vault (TIPO)**.",
                        elem_classes=["pv-help"])
            tipo_output = gr.Radio(tipo.OUTPUTS, value="Tags + natural language", label="Output",
                                   elem_id="pv_tipo_output")
            tipo_length = gr.Radio(tipo.LENGTHS, value="long", label="Length", elem_id="pv_tipo_length")
            tipo_ban = gr.Textbox(label="Never add", placeholder="e.g. text, watermark, *hat (wildcards work)",
                                  lines=1, elem_id="pv_tipo_ban")
            with gr.Row():
                tipo_seed = gr.Number(value=-1, precision=0, label="Seed (-1: random)", elem_id="pv_tipo_seed")
                tipo_temp = gr.Slider(0.1, 1.5, value=0.35, step=0.05, label="Temperature",
                                      elem_id="pv_tipo_temp")
            tipo_into = gr.Radio(INTO, value="Replace", label="Into the editor", elem_id="pv_tipo_into",
                                 info="TIPO keeps your own tags, so Replace does not lose anything")
            tipo_btn = gr.Button("🌱 Expand the positive prompt", variant="primary", elem_id="pv_tipo_run")
            tipo_note = gr.HTML("", elem_id="pv_tipo_note")

        # ============================================================ Qwen
        with gr.Accordion("✍️ Rewrite with Qwen", open=False, elem_id="pv_qwen"):
            gr.Markdown("Your Qwen-VL model rewrites the positive prompt. Settings → **Prompt Vault "
                        "(Qwen / llama-server)**.", elem_classes=["pv-help"])
            qwen_task = gr.Radio(list(qwen_prompts.TEXT_TASKS), value="Tags → sentence", label="Task",
                                 elem_id="pv_qwen_task")
            qwen_instruction = gr.Textbox(label="Instruction", lines=1, visible=False, elem_id="pv_qwen_instruction",
                                          placeholder="e.g. make it night time, keep the character")
            qwen_into = gr.Radio(INTO, value="Replace", label="Into the editor", elem_id="pv_qwen_into")
            qwen_btn = gr.Button("✍️ Rewrite the positive prompt", variant="primary", elem_id="pv_qwen_run")
            qwen_note = gr.HTML("", elem_id="pv_qwen_note")

        # ============================================================ image
        with gr.Accordion("🏞️ Image → Prompt", open=False, elem_id="pv_image"):
            gr.Markdown("WD14 gives exact Danbooru tags (anime, illustration; CPU, no VRAM). Qwen describes "
                        "any image in words, photos too. Both together: WD14's tags steer Qwen's description.",
                        elem_classes=["pv-help"])
            image = gr.Image(label="Image", type="pil", height=300, elem_id="pv_image_input")
            read_with = gr.Radio(READ_WITH, value="WD14 tags", label="Read with", elem_id="pv_read_with")
            with gr.Row():
                wd_general = gr.Slider(0.1, 0.95, value=0.35, step=0.01, label="WD14 tag threshold",
                                       elem_id="pv_wd_general")
                wd_character = gr.Slider(0.1, 0.99, value=0.85, step=0.01, label="WD14 character threshold",
                                         elem_id="pv_wd_character")
            wd_rating = gr.Checkbox(False, label="Add the rating tag (general, sensitive...)", elem_id="pv_wd_rating")
            image_into = gr.Radio(INTO, value="Replace", label="Into the editor", elem_id="pv_image_into")
            read_btn = gr.Button("🔎 Read the image", variant="primary", elem_id="pv_read")
            info_btn = gr.Button("🧾 Use the prompt saved in the image", elem_id="pv_png_info")
            image_note = gr.HTML("", elem_id="pv_image_note")

        # ============================================================ saved / history
        with gr.Accordion("📚 Saved prompts & history", open=False, elem_id="pv_saved_acc"):
            with gr.Row(equal_height=True):
                save_name = gr.Textbox(label="Name", lines=1, scale=3, elem_id="pv_save_name",
                                       placeholder="Saving under an existing name updates it")
                save_btn = gr.Button("📌 Save the editor", variant="primary", scale=1, elem_id="pv_save")
            save_note = gr.HTML("")
            gr.HTML("<div id='pv_saved'></div>")

        # ============================================================ library
        gr.HTML("<div id='pv_library'><div class='pv-loading'>Loading the library…</div></div>")

        with gr.Row(elem_id="pv_ai_row"):
            status_btn = gr.Button("ℹ️ AI model status", elem_id="pv_ai_status")
            stop_btn = gr.Button("⏹️ Stop all AI models", elem_id="pv_ai_stop")
        ai_note = gr.HTML("")
        gr.HTML(f"<div class='pv-version'>Prompt Vault {VERSION} · "
                "<a href='https://github.com/sca-285/sd-webui-prompt-vault/blob/main/CHANGELOG.md' target='_blank'>"
                "what's new</a></div>")

        # ============================================================ logic
        def run_tipo(pos, output, length, ban, seed, temp, into):
            result, note = tipo.expand(pos, output, length, ban, seed, temp)
            return (text.merge(pos, result, into) if result else pos), _note(note)

        def run_qwen(pos, task, instruction, into):
            result, note = qwen.rewrite(pos, task, instruction)
            return (text.merge(pos, result, into) if result else pos), _note(note)

        def run_read(img, how, general, character, rating, pos, into):
            if img is None:
                return pos, _note("Load an image first.")
            notes, result = [], ""
            tags = ""
            if how.startswith("WD14"):
                tags, note, scored = wd14.tag(img, general, character, rating)
                notes.append(note)
                if scored:
                    top = ", ".join(f"{t} {p:.0%}" for t, p in scored[:8])
                    notes.append(f"<span class='pv-scores'>{top}{' …' if len(scored) > 8 else ''}</span>")
                result = tags
            if how == "Qwen tags":
                result, note = qwen.read_image(img, "tags")
                notes.append(note)
            elif "Qwen description" in how:
                desc, note = qwen.read_image(img, "description", hint_tags=tags)
                notes.append(note)
                result = f"{tags}, {desc}" if tags and desc else (desc or tags)
            return (text.merge(pos, result, into) if result else pos), _note("<br>".join(n for n in notes if n))

        def use_info(img):
            found = _generation_info(img)
            if not found:
                return gr.update(), gr.update(), _note("This image carries no generation info.")
            return found[0], found[1], _note("Prompt taken from the image's generation info.")

        def image_changed(img):
            if img is not None and _generation_info(img):
                return _note("This image carries its prompt: 🧾 puts it in the editor.")
            return ""

        def save_prompt(name, pos, neg, img):
            try:
                entry = store.save_prompt(name, pos, neg, _thumb(img))
                return _note(f"Saved as “{entry['name']}”."), ""
            except store.VaultError as exc:
                return _note(str(exc)), gr.update()

        def stop_all():
            stopped = llama.stop_all()
            if wd14.unload():
                stopped.append("WD14")
            return _note(("Stopped: " + ", ".join(stopped)) if stopped else "Nothing was running.")

        def status():
            lines = llama.status_all().split("\n")
            lines.append("WD14: loaded" if wd14._state["session"] is not None else "WD14: not loaded")
            return _note("<br>".join(lines))

        pull.click(None, _js=JS_PULL, inputs=[target, positive, negative], outputs=[target, positive, negative])
        send.click(None, _js=JS_SEND, inputs=[target, positive, negative], outputs=[target, positive, negative])
        clear.click(lambda: ("", ""), outputs=[positive, negative])

        tipo_btn.click(run_tipo, inputs=[positive, tipo_output, tipo_length, tipo_ban, tipo_seed, tipo_temp,
                                         tipo_into], outputs=[positive, tipo_note])
        qwen_task.change(lambda t: gr.update(visible=t == "Follow my instruction"), inputs=[qwen_task],
                         outputs=[qwen_instruction])
        qwen_btn.click(run_qwen, inputs=[positive, qwen_task, qwen_instruction, qwen_into],
                       outputs=[positive, qwen_note])
        read_btn.click(run_read, inputs=[image, read_with, wd_general, wd_character, wd_rating, positive, image_into],
                       outputs=[positive, image_note])
        info_btn.click(use_info, inputs=[image], outputs=[positive, negative, image_note])
        image.change(image_changed, inputs=[image], outputs=[image_note])
        save_btn.click(save_prompt, inputs=[save_name, positive, negative, image], outputs=[save_note, save_name]) \
            .then(None, _js=JS_RELOAD_SAVED)
        status_btn.click(status, outputs=[ai_note])
        stop_btn.click(stop_all, outputs=[ai_note])

    return tab
