# Notices

## KGen / TIPO

`lib_vault/tipo.py` adapts code from KGen by Shih-Ying Yeh (KohakuBlueLeaf),
<https://github.com/KohakuBlueleaf/KGen>, licensed under the Apache License 2.0:

- the TIPO request format (`apply_tipo_prompt`), the parsing of its answers
  (`parse_tipo_result`), the request planning (`parse_request`), the post-processing
  and the length targets, from `kgen/executor/tipo.py` and `kgen/metainfo.py`;
- the tag formatting (`apply_format`, `separate_tags`), from `kgen/formatter.py`.

`data/tipo_meta_tags.txt` is `kgen/tag-list/meta.txt` from the same project.

Changes: generation goes to llama-server's `/completion` endpoint instead of
llama-cpp-python or transformers; randomness uses a per-call seeded generator;
banned tags accept wildcards; the retry loop is shorter.

A copy of the Apache License 2.0 is at <https://www.apache.org/licenses/LICENSE-2.0>.

## Models

No model is included. They are downloaded from their authors' repositories, or pointed
to by the user, and each keeps its own license:

- TIPO models, KohakuBlueLeaf: <https://huggingface.co/KBlueLeaf>
- WD14 tagger v3 models, SmilingWolf: <https://huggingface.co/SmilingWolf>
- Qwen-VL models, Qwen: <https://huggingface.co/Qwen>
