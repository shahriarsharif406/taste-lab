"""Check the Gemini key. Run:  python scripts/smoke_gemini.py   (needs GEMINI_API_KEY in env)"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tastelab import config
from tastelab.llm import llm_from_env

config.load_dotenv()
llm = llm_from_env()
print("key set:", llm.available, "| model:", llm.model)
out = llm.json('Reply with JSON {"ok": true, "word": "hello"}')
print("RESULT:", out)
print("model used:", llm.model)
print("WARNINGS:", llm.warnings or "none")
