"""
Quick launcher for the SARAS Desktop UI.
Usage:
    python run_ui.py
"""
import sys
from app.bootstrap import build_application
from ui.app_window import launch


def main():
    print("Starting SARAS Desktop UI...")
    app = build_application()
    launch(app)


if __name__ == "__main__":
    sys.exit(main())
