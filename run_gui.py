"""Launch the SM Configuration API Explorer GUI.

Usage:
    python run_gui.py
"""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main import main

if __name__ == "__main__":
    main()
