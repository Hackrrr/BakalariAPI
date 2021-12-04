"""Prakticky pouze placeholder, aby šlo spustit `bakalarishell` přímo ze zdroje ze složky nebo přes `python -m bakalarishell`"""

try:
    from .main import main
except ImportError:
    from main import main  # type: ignore

main()
