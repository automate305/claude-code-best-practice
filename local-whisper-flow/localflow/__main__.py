"""Entry point: `python -m localflow`."""

from .app import App
from .config import config_path, load_config


def main() -> None:
    config = load_config()
    print(f"LocalFlow — config: {config_path()}")
    try:
        App(config).run()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
