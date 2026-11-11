"""Settings. Everything can be overridden with environment variables or a .env file."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Load a simple KEY=VALUE .env if present (no extra dependency).
_env = ROOT / ".env"
if _env.exists():
    for line in _env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

PDF_DIR = Path(os.getenv("PDF_DIR", ROOT / "Files"))
INDEX_DIR = Path(os.getenv("INDEX_DIR", ROOT / "index"))
LOG_DIR = Path(os.getenv("LOG_DIR", ROOT / "logs"))
STATIC_DIR = ROOT / "app" / "static"

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))

TOP_K = int(os.getenv("TOP_K", "4"))
CANDIDATES = int(os.getenv("CANDIDATES", "8"))
RRF_K = 60

# Loose gate: stops a question only if none of its words appear in the best matches AND the best
# vector similarity is low. bge-small scores unrelated text around 0.45-0.52 and relevant text above 0.55,
# so 0.60 is a conservative cut-off (measured on the sample set; see eval/results.md).
GATE_MIN_COSINE = float(os.getenv("GATE_MIN_COSINE", "0.60"))
