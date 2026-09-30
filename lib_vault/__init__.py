"""Prompt Vault: a prompt workbench for the Forge family of Stable Diffusion WebUIs.

store     the tag library, saved prompts and history, kept outside the extension
text      splitting and joining prompts
llama     llama-server processes (Qwen and TIPO), started on demand, stopped when idle
qwen      Qwen-VL: image -> prompt and prompt rewriting
tipo      TIPO: prompt expansion
wd14      WD14 tagger: image -> booru tags
muse      Muse: timed idea cards from packs, shown by a floating button
api       the HTTP routes the tab's JavaScript talks to
ui        the tab
"""

TAG = "[Prompt Vault]"
