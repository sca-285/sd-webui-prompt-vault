"""Prompt Vault: a prompt workbench for the Forge family of Stable Diffusion WebUIs.

store     the tag library, saved prompts and history, kept outside the extension
text      splitting and joining prompts
arrange   putting the tags of a prompt in order, from what the library knows of them
llama     llama-server processes (Qwen and TIPO), started on demand, stopped when idle
qwen      Qwen-VL: image -> prompt and prompt rewriting
tipo      TIPO: prompt expansion
wd14      WD14 tagger: image -> booru tags
vocab     what Muse takes from the library: poses and style families
kinks     Muse's NSFW layers: kinks and anatomy tags
acts      sex acts by family, and which kink goes with which act
when      the hour and the sky, and what they allow of the other parts
looks     looks, jobs, camera, light and colour: the parts Muse adds around a scene
muse      Muse: prompt ideas from scenes, shown on a floating card
api       the HTTP routes the tab's JavaScript talks to
ui        the tab
"""

VERSION = "1.1.0"
TAG = "[Prompt Vault]"
