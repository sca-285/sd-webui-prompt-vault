"""The WebUI's paths, for the checks: a data folder of their own (tests/run.py makes one per check)."""
import os

data_path = os.environ["PV_TEST_DATA"]
models_path = os.path.join(data_path, "models")
extensions_dir = os.path.join(data_path, "extensions")
