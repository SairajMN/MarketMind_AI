import sys
from pathlib import Path

# Add project root to Python path so the `backend` package is importable
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.app.extension_api import app
