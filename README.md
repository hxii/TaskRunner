# TaskRunner
TaskRunner is a **simple** sequential task runner written in Python with support for variables, dependencies, helpers and tasks.

I made it to automate simple, recurring tasks without having to touch code.

Read more about [Tasks](docs/tasks.md), [Variables](docs/variables.md) and [Helpers](docs/helpers.md).

## Example Task File
```YAML
tasks:
  display_welcome:
    text: |
        Welcome to TaskRunner!

        TaskRunner is a simple, sequential task runner built with Python and is based on YAML files.
        The point is for it to not be robust or feature complete, but to be quick to deploy and configure.
        See `tasks.yml` to see how this task run is configured.
    python_task:
      text: |
          We can run Python code as well, and check the output.
          The python code is not parsed by TaskRunner, but we can use `python -c` to achieve this.

          Before running this, we can run a helper to make sure we have access to Python, for example.
      run: python -c "from pprint import pprint; pprint('This was printed by Python')"
      prerequisites: helpers.command_exists(python) helpers.command_exists(brew)
      show_output: True
helpers:
  command_exists:
    text: Does COMMAND exist
    command: command -v {}

```

## Running things
```
usage: TaskRunner [-h] [-V] [-v] [-q] [-d] [-t] taskfile

Simple, sequential task runner

positional arguments:
  taskfile

options:
  -h, --help       show this help message and exit
  -V, --version    show program's version number and exit
  -v, --verbose    Verbose output.
  -q, --quiet      Do not output anything except errors.
  -d, --dry_run    Only show the intended command, without actually running anything.
  -t, --text-only  Only show task text, omitting the output.
```
