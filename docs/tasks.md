# Tasks
A task can be define as simply as:
```YAML
tasks:
    my_task:
        run: echo "Hello World"
```

## Options
- `text`: The text a task should announce before it executes.
- `run`: The command a task should run. `shell=True` if a string is passed, `shell=False` if a list is passed.
- `success`: The successful return code a task should anticipate. 0 by default.
- `each`: Accepts a list (or variable of list) that the `run` command should iterate through.
- `show_output`: Whether to display the output of the executed command.
- `check`: A regex string that the output should be checked against.
- `require_input`: Simply passing `True` will require user input to proceed. Passing a string will display said string before accepting input from the user.
    If an input was provided, it can be retrieved from `variables`. For example, if a task is called `checkpy`, the input can be retrieved with `variables.checkpy_output`.
- `cwd`: The working directory a task should be executed in.
- `prerequisites`: (WIP) A string of `helpers` that should be checked prior to executing `run`.