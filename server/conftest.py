import os
import tempfile
from pathlib import Path
import pytest

# Create a temporary directory for the test suite
test_dir = tempfile.TemporaryDirectory()
temp_path = Path(test_dir.name)

# Set the environment variable BEFORE any modules import src.infra.sqlite
os.environ["UNMESSIT_DATA_DIR"] = str(temp_path)

# Now we can safely import our app modules
import src.infra.sqlite

@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    # Make sure the directory exists and initialize the schema
    os.makedirs(temp_path, exist_ok=True)
    src.infra.sqlite.init_db()
    
    yield
    
    # Cleanup after tests
    test_dir.cleanup()
