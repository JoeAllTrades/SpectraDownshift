#!/usr/bin/env python3

"""
Main entry point for launching the Spectradownshift GUI application.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

# Import the main application window and profile manager from our package.
from Spectradownshift.gui.app import MainWindow
from Spectradownshift.config import ProfileManager

# Ensure all necessary modules are available.
try:
    from Spectradownshift.processor import AudioProcessor
except ImportError as e:
    print(f"Error: A required module is missing or could not be loaded: {e}", file=sys.stderr)
    print("Please make sure all dependencies from requirements.txt are installed.", file=sys.stderr)
    sys.exit(1)


def main():
    """Initializes and runs the Qt application."""

    # Instantiate a ProfileManager to handle application profiles.
    # This keeps path management separate from the GUI logic.
    profile_manager = ProfileManager(Path("profiles.json"))

    app = QApplication(sys.argv)

    # The main window requires the profile manager for its operations.
    window = MainWindow(pm=profile_manager)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()