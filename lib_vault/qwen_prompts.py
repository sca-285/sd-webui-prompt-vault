"""What to ask Qwen, and how to clean up what comes back.

Qwen-VL writes prose by default. It follows instructions well enough to produce
a comma-separated tag list instead, but it still likes to open with "Sure, here
are the tags:" and to end with a sentence, so both directions need tidying
afterwards. The cleanup is deliberately dumb and local - no model is trusted to
have obeyed the format.
"""

from __future__ import annotations

import re

TAG_PROMPT = (
    "Describe this image as a list of short booru-style tags for an image "
    "generation prompt.\n"
    "Rules:\n"
    "- output ONE line: tags separated by commas, nothing else\n"
    "- no sentences, no numbering, no bullet points, no headings, no quotes\n"
    "- lowercase, 1 to 3 words per tag\n"
    "- cover, in this order: how many subjects and who they are, hair, eyes, "
    "expression, clothing, pose and what they are doing, the setting, the "
    "lighting, the framing or camera angle, and the art style\n"
    "- only describe what is actually visible; never guess names or text\n"
    "Start the answer with the first tag."
)

DESCRIPTION_PROMPT = (
    "Write one vivid paragraph describing this image, as a prompt for an image "
    "generation model.\n"
    "Rules:\n"
    "- one paragraph, no preamble, no bullet points, no headings\n"
    "- do not start with 'The image shows' or 'This image'; start with the subject\n"
    "- cover the subject, what they are doing, clothing, setting, lighting, "
    "colours, mood, framing and art style\n"
    "- only describe what is actually visible; never guess names or text"
)

TAGGED_DESCRIPTION_PROMPT = (
    DESCRIPTION_PROMPT
    + "\n- a tagger found these in the image; use the ones you can see, in your own words: {tags}"
)

# ---- text only: rewriting a prompt the user already has

_KEEP = (
    "Keep anything in angle brackets such as <lora:name:0.8> exactly as it is. "
    "Keep weights such as (red hair:1.2) as they are. "
)

TEXT_TASKS = {
    "Tags → sentence": (
        "Rewrite this image generation prompt, a list of tags, as one natural, vivid paragraph "
        "for a model that understands plain English (SDXL, Flux). Keep every detail the tags give; "
        "add nothing that contradicts them. " + _KEEP
        + "Answer with the paragraph only, no preamble.\n\nPrompt: {prompt}",
        "description",
    ),
    "Sentence → tags": (
        "Rewrite this image generation prompt as a list of short Danbooru-style tags, comma-separated, "
        "lowercase, most important first. Keep every detail; add nothing new. " + _KEEP
        + "Answer with the one line of tags only.\n\nPrompt: {prompt}",
        "tags",
    ),
    "Arrange tags": (
        "Tidy this image generation prompt, a list of Danbooru-style tags. Put the tags in this order: "
        "quality, how many people and who, body, face and hair, expression, clothing, accessories, pose "
        "and action, place, time and weather, lighting, colour, camera and framing, style. Merge "
        "duplicates and near-duplicates into one tag; when two tags contradict each other, keep the "
        "first; correct misspelt tags to their Danbooru spelling. Add no new tag and drop no detail. "
        + _KEEP + "Answer with the one line of tags only.\n\nPrompt: {prompt}",
        "tags",
    ),
    "Translate to English": (
        "Translate this image generation prompt into English. Keep its form: if it is a tag list, "
        "answer with a tag list; if it is prose, answer with prose. Words that are already English stay "
        "as they are. " + _KEEP + "Answer with the translation only.\n\nPrompt: {prompt}",
        "keep",
    ),
    "Follow my instruction": (
        "Here is an image generation prompt and an instruction for changing it. Apply the instruction "
        "and change nothing else. Keep the prompt's form: a tag list stays a tag list, prose stays prose. "
        + _KEEP + "Answer with the new prompt only.\n\nInstruction: {instruction}\n\nPrompt: {prompt}",
        "keep",
    ),
}

# Openers the model adds no matter how firmly it is told not to. These are kept
# deliberately tight: an earlier version matched everything up to the end of the
# line, which on "Certainly! A young woman stands in a sunlit classroom, ..."
# ate the whole first clause. Only the interjection itself goes, and only a
# "here is ...:" lead-in that really ends in a colon.
_INTERJECTION = re.compile(
    r"^\s*(?:sure|certainly|of course|okay|ok|alright|absolutely|got it)"
    r"\s*[!,.—-]+\s*",
    re.IGNORECASE,
)
_HERE_IS = re.compile(r"^\s*here\s+(?:is|are)\b[^:\n]{0,60}:\s*", re.IGNORECASE)


def _strip_preamble(text):
    for _ in range(2):          # "Sure! Here are the tags:" is two of them
        before = text
        text = _INTERJECTION.sub("", text)
        text = _HERE_IS.sub("", text)
        if text == before:
            break
    return text
_THINK = re.compile(r"<think>.*?</think>\s*", re.IGNORECASE | re.DOTALL)
_LEAD_MARKER = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")
_LEAD_ARTICLE = re.compile(r"^(?:a|an|the)\s+", re.IGNORECASE)
_CODE_FENCE = re.compile(r"^\s*```[a-z]*\s*|\s*```\s*$", re.IGNORECASE)


def _strip_wrapper(text):
    text = _THINK.sub("", text or "")
    text = _CODE_FENCE.sub("", text)
    return text.strip()


def clean_tags(text, max_words=4):
    """The model's answer as a de-duplicated comma-separated tag line.

    Splits on commas and newlines, drops list markers, lowercases, and throws
    away anything that is clearly a sentence rather than a tag."""
    text = _strip_preamble(_strip_wrapper(text))

    pieces = []
    for chunk in re.split(r"[,\n]", text):
        tag = _LEAD_MARKER.sub("", chunk).strip()
        tag = tag.strip(" .;:\"'`()[]")
        tag = tag.replace("_", " ")
        tag = re.sub(r"\s+", " ", tag).lower()
        if not tag:
            continue
        # A whole sentence leaked through: too many words, or it ends in a verb
        # phrase with its own punctuation.
        if len(tag.split()) > max_words:
            continue
        tag = _LEAD_ARTICLE.sub("", tag).strip()
        if not tag or tag in {"tags", "tag list", "image", "no text"}:
            continue
        pieces.append(tag)

    seen = {}
    for tag in pieces:
        seen.setdefault(tag, None)
    return ", ".join(seen)


def clean_description(text):
    """The model's answer as one tidy paragraph."""
    text = _strip_preamble(_strip_wrapper(text))
    text = re.sub(
        r"^\s*(this|the)\s+(image|picture|photo|illustration|artwork)\s+"
        r"(shows|depicts|features|is of|captures|presents)\s*",
        "", text, flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    if text[:1].islower():
        text = text[0].upper() + text[1:]
    return text
