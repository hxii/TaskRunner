import argparse
import logging
from taskrunner import TaskRunner, logger

parser = argparse.ArgumentParser(
    prog="TaskRunner", description="Simple, sequential task runner"
)

parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("-q", "--quiet", action="store_true")
parser.add_argument("taskfile")

args = parser.parse_args()

if args.verbose:
    logger.setLevel(logging.DEBUG)

def run():
    tr = TaskRunner(args.taskfile, quiet=args.quiet)
    tr.run()
    
if __name__ == "__main__":
    run()