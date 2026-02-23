import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui.launcher import LauncherWindow


def main():
    app = LauncherWindow()
    app.run()


if __name__ == "__main__":
    main()
