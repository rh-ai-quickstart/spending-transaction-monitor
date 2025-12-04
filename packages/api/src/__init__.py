"""FastAPI application for spending-monitor"""

from pathlib import Path
import sys

# Ensure the src directory itself is on sys.path so absolute imports like
# ``import services...`` resolve when running under uvicorn.
_BASE = Path(__file__).resolve().parent
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))

__version__ = '0.0.0'
