"""Check the Gemini key. Run:  python scripts/smoke_gemini.py   (needs GEMINI_API_KEY in env)"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tastelab import config
from tastelab.llm import llm_from_env

config.load_dotenv()
import os
raw = os.environ.get("GEMINI_API_KEY", "")
bad = [i for i, ch in enumerate(raw) if not (32 < ord(ch) < 127)]
print("raw key length:", len(raw), "| bad characters at positions:", bad or "none", "| starts with:", raw[:3])
llm = llm_from_env()
print("key set:", llm.available, "| model:", llm.model)
import time
t0 = time.time()
out = llm.json('Reply with JSON {"ok": true, "word": "hello"}')
print("RESULT:", out, "| seconds:", round(time.time() - t0, 1))
print("model used:", llm.model)
print("WARNINGS:", llm.warnings or "none")
