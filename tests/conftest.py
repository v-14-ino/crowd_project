import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app
from api.auth import get_current_user
from models.models import User

def mock_get_current_user():
    return User(id=999, email="test@municipal.gov", role="officer")

app.dependency_overrides[get_current_user] = mock_get_current_user
