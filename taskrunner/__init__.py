import argparse
import logging
from .main import TaskRunner, logger

parser = argparse.ArgumentParser(
    prog="TaskRunner", description="Simple, sequential task runner"
)

parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")
parser.add_argument(
    "-q", "--quiet", action="store_true", help="Do not output anything except errors."
)
parser.add_argument(
    "-d",
    "--dry_run",
    action="store_true",
    help="Only show the intended command, without actually running anything.",
)
parser.add_argument(
    "-t",
    "--text-only",
    action="store_true",
    help="Only show task text, omitting the output.",
)
parser.add_argument("taskfile")

args = parser.parse_args()

if args.verbose:
    logger.setLevel(logging.DEBUG)


def run():
    tr = TaskRunner(
        args.taskfile, quiet=args.quiet, dry_run=args.dry_run, text_only=args.text_only
    )
    try:
        tr.run()
    except KeyboardInterrupt:
        print("\n!!!\nABORTED BY USER\n!!!")
