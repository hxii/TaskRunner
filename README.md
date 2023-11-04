# TaskRunner
TaskRunner is a simple sequential task runner written in Python with support for variables, dependencies, helpers and tasks.

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
    command: python -c "from pprint import pprint; pprint('This was printed by Python')"
    prerequisites: helpers.command_exists(python) helpers.command_exists(abracadbra)
    shell: True
helpers:
  command_exists:
    text: Does COMMAND exist
    command: command -v {}

```

## Running things
`taskrunner tasks.yml`
`-v` for verbose
`-q` for quiet
