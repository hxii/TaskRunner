import argparse
import logging
from pathlib import Path
from sys import version as python_version
from sys import version_info

from taskrunner import __version__

from .main import TaskRunner, logger

assert version_info >= (3, 10), f"Python >= 3.10 required. You've got {python_version}"

parser = argparse.ArgumentParser(prog="TaskRunner", description="Simple, sequential task runner")

parser.add_argument("-c", "--check-only", action="store_true", help="Only validate YAML schema and exit.")
parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")
parser.add_argument("-q", "--quiet", action="store_true", help="Do not output anything except errors.")
parser.add_argument(
    "-d", "--dry_run", action="store_true", help="Only show the intended command, without actually running anything."
)
parser.add_argument(
    "-t",
    "--text-only",
    action="store_true",
    help="Only show task text, omitting the output.",
)

parser.add_argument("taskfile", help="A valid YAML task file", type=Path)

args = parser.parse_args()

if args.verbose:
    logger.setLevel(logging.DEBUG)


def run():
    tr = TaskRunner(
        args.taskfile, quiet=args.quiet, dry_run=args.dry_run, text_only=args.text_only, check_only=args.check_only
    )
    try:
        tr.run()
    except KeyboardInterrupt:
        print("\n!!!\nABORTED BY USER\n!!!")
