import launch

# WD14 runs on onnxruntime. Anything that already provides it (onnxruntime-gpu,
# onnxruntime-directml...) is left alone. Qwen and TIPO run in llama-server, a
# separate program, so they need nothing installed here.
if not any(launch.is_installed(name) for name in
           ("onnxruntime", "onnxruntime-gpu", "onnxruntime-directml", "onnxruntime-silicon", "ort-nightly")):
    launch.run_pip("install onnxruntime", "Prompt Vault requirement: onnxruntime (WD14 tagger)")
