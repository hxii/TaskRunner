# Helpers
Helpers are auxiliary (often repeating) commands that are exempt from the sequence, but can be run ad-hoc when requested by tasks, for example checking a command exists.
```YAML
helpers:
    command_exists:
        text: Check that a command exists
        run: command -v {}
        shell: True
    python_312_not_available:
        run: pyenv versions --skip-envs --skip-aliases | grep -q "3.12"
        success: 1
        shell: True
```