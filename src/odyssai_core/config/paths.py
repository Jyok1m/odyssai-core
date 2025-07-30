from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
SECRET_DIR = BASE_DIR / ".secrets"
TEST_DIR = BASE_DIR / "tests"
