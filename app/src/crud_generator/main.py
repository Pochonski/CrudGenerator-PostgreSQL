from crud_generator.application import ApplicationFlow
from crud_generator.ui.cli import Cli


def main() -> None:
    raise SystemExit(ApplicationFlow(Cli()).run())


if __name__ == "__main__":
    main()
