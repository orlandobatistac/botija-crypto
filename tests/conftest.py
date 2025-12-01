"""
Pytest configuration for tests
Adds backend directory to Python path and sets correct working directory
"""

import sys
import os
from pathlib import Path

# Get paths
tests_dir = Path(__file__).parent
project_root = tests_dir.parent
backend_path = project_root / "backend"

# Add backend directory to path so 'app' module can be imported
sys.path.insert(0, str(backend_path))

# Change working directory to backend so relative DB paths work
os.chdir(backend_path)
