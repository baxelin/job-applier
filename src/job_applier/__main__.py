import sys

from job_applier.cli import CommandLine


def main() -> None:
    raise SystemExit(CommandLine().run(sys.argv[1:]))


if __name__ == "__main__":
    main()
