#!/usr/bin/env python3
"""
DeepSeek-OCR GPU verification script for DGX Spark
-------------------------------------------------
This script confirms:
 - CUDA visibility (torch + GPU)
 - DeepSeek-OCR dynamic module import works
 - Model loads successfully on GPU
"""

import torch
import importlib
import importlib.util
import sys
import pathlib
import types
from transformers import AutoConfig

print("=" * 60)
print("🚀  DeepSeek-OCR GPU Test")
print("=" * 60)
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("Device:", torch.cuda.get_device_name(0))
print()

# --------------------------------------------------------------
# 1️⃣  Load configuration (also downloads model files to cache)
# --------------------------------------------------------------
print("Loading DeepSeek-OCR configuration…")
config = AutoConfig.from_pretrained("deepseek-ai/deepseek-ocr", trust_remote_code=True)

# --------------------------------------------------------------
# 2️⃣  Locate cached model files
# --------------------------------------------------------------
home = pathlib.Path.home()
possible_dirs = [
    home / ".cache/huggingface/modules/transformers_modules",
    home / ".cache/huggingface/hub",
]
matches = []
for root in possible_dirs:
    if root.exists():
        matches.extend(root.rglob("modeling_deepseekocr.py"))

if not matches:
    print("❌  modeling_deepseekocr.py not found in cache!")
    print("   Searched in:")
    for d in possible_dirs:
        print("   -", d)
    sys.exit(1)

mod_path = matches[0].parent
print(f"Found DeepSeek-OCR module under: {mod_path}")

# --------------------------------------------------------------
# 3️⃣  Build a temporary package namespace so relative imports work
# --------------------------------------------------------------
pkg_name = "deepseek_ocr"
pkg = types.ModuleType(pkg_name)
pkg.__path__ = [str(mod_path)]  # where modeling_deepseekocr.py lives
sys.modules[pkg_name] = pkg

spec = importlib.util.spec_from_file_location(
    f"{pkg_name}.modeling_deepseekocr", mod_path / "modeling_deepseekocr.py"
)
model_mod = importlib.util.module_from_spec(spec)
sys.modules[f"{pkg_name}.modeling_deepseekocr"] = model_mod
spec.loader.exec_module(model_mod)

# --------------------------------------------------------------
# 4️⃣  Instantiate the model
# --------------------------------------------------------------
model_cls = getattr(model_mod, "DeepseekOCRModel", None) or getattr(
    model_mod, "DeepseekOCRForCausalLM", None
)
if not model_cls:
    print("❌  Could not find DeepseekOCRModel class in loaded module.")
    sys.exit(1)

print("Instantiating model… (this may take a minute)")
model = model_cls.from_pretrained("deepseek-ai/deepseek-ocr", trust_remote_code=True)
print("✅  Model loaded successfully!")

# --------------------------------------------------------------
# 5️⃣  Optional: print GPU memory and model summary
# --------------------------------------------------------------
if torch.cuda.is_available():
    print(f"GPU memory allocated: {torch.cuda.memory_allocated() / 1e6:.2f} MB")
    print(f"GPU memory reserved:  {torch.cuda.memory_reserved() / 1e6:.2f} MB")

print("🎉  DeepSeek-OCR is operational on this DGX Spark GPU environment.")
