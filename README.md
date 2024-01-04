# TaskRunner
TaskRunner is a **simple** sequential task runner written in Python with support for variables, dependencies, helpers and tasks.

I made it to automate simple, recurring tasks without having to touch code.

Read more about [Tasks](docs/tasks.md), [Variables](docs/variables.md) and [Helpers](docs/helpers.md).

## Running things
```
usage: TaskRunner [-h] [-c] [-V] [-v] [-q] [-d] [-t] taskfile

Simple, sequential task runner

positional arguments:
  taskfile          A valid YAML task file

options:
  -h, --help        show this help message and exit
  -c, --check-only  Only validate YAML schema and exit.
  -V, --version     show program's version number and exit
  -v, --verbose     Verbose output.
  -q, --quiet       Do not output anything except errors.
  -d, --dry_run     Only show the intended command, without actually running anything.
  -t, --text-only   Only show task text, omitting the output.
```
