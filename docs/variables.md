# Variables
Variables (for the lack of a better term) are intended to be used in commands.
Variables are defined in taskfiles as a list, for example:
```YAML
variables:
    - brew_packages:
        - awscli
        - hdf5
        - colima
        - docker-buildx
        - cmake
        - libomp
    - thing: |
        This is just text tbh.
        With a newline.
```
The variables you define can then be used in commands, like so:
```YAML
tasks:
    thing:
        run: echo "variables.thing"
        show_output: True
```
The content can also be used in `each`, like so:
```YAML
tasks:
    brew_packages:
        each: variables.brew_packages
        run: brew info {}
```

## Task output
The output of a task is also being saved to a variable, and can be referenced as `variables.<task>_output`.
So if you have a task named `download`, it's output can be referenced with `variables.download_output`.