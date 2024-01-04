import logging
import os
import re
import subprocess
import sys
from abc import ABC
from copy import copy
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path

import yaml
from cerberus import Validator

from taskrunner import __version__

logger = logging.getLogger(__name__)

schema = {
    "information": {"type": "string"},
    "tasks": {
        "type": "dict",
        "keysrules": {"type": "string", "regex": "[a-z][a-z0-9_]+"},
        "required": True,
        "valuesrules": {
            "type": "dict",
            "schema": {
                "description": {"type": "string"},
                "prerequisites": {"type": "string"},
                "run": {"type": ["string", "list"], "schema": {"type": "string"}},
                "each": {
                    "type": ["string", "list"],
                    "schema": {"type": "string"},
                    "dependencies": "run",
                },
                "working_dir": {"type": "string"},
                "env": {"type": "dict", "allow_unknown": True},
                "success_code": {"type": "integer"},
                "require_input": {"type": ["boolean", "string"]},
                "check": {"type": "string"},
                "show_output": {"type": "boolean"},
                "on_success": {
                    "type": ["string", "dict"],
                    "schema": {
                        "command": {"type": "string"},
                        "skip_to": {"type": "string"},
                        "message": {"type": "string"},
                    },
                },
                "on_failure": {
                    "type": ["string", "dict"],
                    "schema": {
                        "command": {"type": "string"},
                        "skip_to": {"type": "string"},
                        "message": {"type": "string"},
                    },
                },
            },
        },
    },
    "variables": {
        "type": "dict",
        "keysrules": {"type": "string", "regex": "[a-z][a-z0-9_]+"},
    },
    "helpers": {"type": "dict"},
}


class color:
    PURPLE = "\033[95m"
    GRAY = "\033[2m"
    CYAN = "\033[96m"
    DARKCYAN = "\033[36m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


class TaskRunner:
    _quiet: bool = False
    _dry_run: bool = False
    tasks: list["Task"] = []
    variables: dict = {}
    helpers: dict[str, "Helper"] = {}
    environment: dict = os.environ.copy()

    def __init__(self, task_file: str, quiet: bool, dry_run: bool, text_only: bool, check_only: bool) -> None:
        self._decide_logger_format()
        TaskRunner.quiet = quiet
        TaskRunner.dry_run = dry_run
        TaskRunner.text_only = text_only
        TaskRunner.check_only = check_only
        task_path = Path(task_file)
        if not task_path.exists():
            raise TaskRunnerException(f"{task_path} doesn't exist. Aborting!")
        self.task_path = task_path

    def _header_info(self, header: str, text: str) -> str:
        return f"{color.BOLD}{header}:{color.END} {text}"

    def _decide_logger_format(self):
        _format = "%(message)s" if logger.getEffectiveLevel() >= 20 else "%(levelname)-8s - %(funcName)s - %(message)s"
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=_format)

    def _validate_yaml(self, data: dict) -> tuple[bool, str]:
        validator = Validator(schema)
        if not validator.validate(data):
            errors = self._flatten_errors(validator.errors)
            return False, "\n".join(errors)
        return True, "Valid"

    def _flatten_errors(self, error_obj: dict, key_path: list | None = None):
        """
        Flatten a JSON dict of YAML errors to a more humanly readable format.

        Args:
            error_obj (dict): error dict from cerberus
            key_path (list, optional): The "path" to the error. Defaults to None.

        Returns:
            list: A list of error messages
        """
        messages = []

        if key_path is None:
            key_path = []

        if isinstance(error_obj, dict):
            for key, value in error_obj.items():
                messages.extend(self._flatten_errors(value, [*key_path, key]))
        elif isinstance(error_obj, list) and all(isinstance(i, dict) for i in error_obj):
            # Special handling when a list contains dictionary elements
            for item in error_obj:
                messages.extend(self._flatten_errors(item, key_path))
        elif isinstance(error_obj, list):
            # We've reached an error message list
            formatted_path = " -> ".join(key_path)
            for error in error_obj:
                messages.append(f"{formatted_path}: {error}")
        else:
            # Individual error message
            formatted_path = " -> ".join(key_path)
            messages.append(f"{formatted_path}: {error_obj}")

        return messages

    def _parse_taskfile(self) -> bool:
        """Load the YAML file and parse the sections within."""
        parsed_yaml = yaml.safe_load(self.task_path.open(encoding="UTF-8"))
        valid, message = self._validate_yaml(parsed_yaml)
        if TaskRunner.check_only:
            exit(not valid)
        logger.info(f"{color.BOLD}YAML Valid:{color.END} {valid}")
        if not valid:
            raise TaskRunnerException(message)
        if "information" in parsed_yaml:
            logger.info(f"{color.BOLD}Information:{color.END} {parsed_yaml['information'].strip()}")
        if "variables" in parsed_yaml:
            self._populate_variables(parsed_yaml["variables"])
        if "helpers" in parsed_yaml:
            self._populate_helpers(parsed_yaml["helpers"])
        if "tasks" in parsed_yaml:
            self._populate_tasks(parsed_yaml["tasks"])
        return parsed_yaml

    def _populate_tasks(self, tasks: dict):
        logger.info(f"{color.BOLD}Tasks:{color.END} {len(tasks)}")
        for name, config in tasks.items():
            self.tasks.append(Task(name=name, **config))
            logger.debug(f"Task {name} added.")

    def _populate_variables(self, variables: dict):
        logger.info(f"{color.BOLD}Variables:{color.END} {len(variables)}")
        for name, value in variables.items():
            self.variables[name] = value
            logger.debug(f"Variable {name} added.")

    def _populate_helpers(self, helpers: list):
        logger.info(f"{color.BOLD}Helpers:{color.END} {len(helpers)}")
        for name, config in helpers.items():
            self.helpers[name] = Helper(name=name, **config)
            logger.debug(f"Helper {name} added.")

    def _parse_each_loop(self, items: str | list) -> list:
        if isinstance(items, str):
            var = self._parse_variables_in_command(items)
            return self._get_variable(var)
        return items

    def _get_prerequisite(self, prerequisite: str):
        pass

    def _process_prerequisites(self, prerequisites: str) -> None:
        prerequisite_list = prerequisites.split(" ") if prerequisites != "" else []
        prerequisite_list = [pre for pre in prerequisite_list if pre.startswith("helpers.")]
        # Filter out whatever doesn't start with "helper"
        for prerequisite in prerequisite_list:
            helper_pattern = r"(?:helpers\.)(\w+)(?:\((.*?)\))?"
            helper, _args = re.findall(helper_pattern, prerequisite)[0]
            if not self.helpers.get(helper):
                logger.error(f"Helper {helper} is not valid")
                continue
            _helper = copy(self.helpers[helper])
            _helper._args = _args.split()
            _helper.run = _helper.run.format(*_helper._args)
            _helper._execute_task()

    def _parse_prerequisites_in_task(self, prerequisites: str) -> list["Task"]:
        # TODO: Remove?
        prerequisite_list = prerequisites.split(" ") if prerequisites != "" else []
        for i, prerequisite in enumerate(prerequisite_list):
            if prerequisite.startswith("helpers"):
                helper_pattern = r"(?:helpers\.)(\w+)(?:\((.*?)\))?"
                helper, _args = re.findall(helper_pattern, prerequisite)[0]
                try:
                    helper_proto = self.helpers[helper]
                    _helper = replace(helper_proto)
                    prerequisite_list[i] = _helper
                    prerequisite_list[i]._args = _args.split()
                except KeyError:
                    logger.error(f"Helper {helper} not found.")
        return prerequisite_list

    def run(self):
        if TaskRunner.quiet:
            logger.setLevel(logging.ERROR)
        logger.info(f"{color.BOLD}{color.DARKCYAN}[TaskRunner {__version__}]{color.END}")
        logger.info(f"{color.BOLD}Task File:{color.END} {self.task_path.absolute()}")
        self._parse_taskfile()
        logger.info(f"{color.BOLD}Dry Run:{color.END} {TaskRunner.dry_run}")
        logger.info("---")
        logger.info(f"{color.BOLD}Started:{color.END} {datetime.today()}")
        for index, task in enumerate(self.tasks, start=1):
            TaskRunner.current_task = index
            self._process_prerequisites(task.prerequisites)
            task._execute_task()
        logger.info(f"{color.BOLD}Ended:{color.END} {datetime.today()}")


@dataclass
class Executable(ABC):
    name: str
    """Name of the task."""
    description: str = ""
    """The intro text to display."""
    run: list | str = ""
    """The command that needs to be executed. List for `shell=False`."""
    working_dir: str = "."
    """The working directory where the commands should be executed in."""
    each: list = field(default_factory=list)
    """Iterator for multiple passes of `run`."""
    success: None | bool = None
    """Was the execution successful."""
    success_code: int = 0
    """The return code we should anticipate for a successful command."""
    output: str = ""
    """The last output the `run` command."""
    commands: list["Command"] = field(default_factory=list)
    """The commands that need to be executed."""
    env: None | dict = None
    """The environment variables."""
    on_success: str | dict = None
    on_failure: str | dict = None

    def _populate_commands(self) -> int:
        """
        Populate `self.commands` with each iteration of `self.each` if it's not an empty list,
        and parse any variables present.
        """
        self.commands = []  # Fixes a weird problem
        # Commands would compound for a helper.
        if not self.run:
            return 0
        if self.each:
            for iteration in self.each:
                if isinstance(self.run, list):
                    self.error("`run` must be a str when using `each`!", True)
                if isinstance(iteration, dict):
                    formatted_command = self.run.format(**iteration)
                elif isinstance(iteration, list):
                    formatted_command = self.run.format(*iteration)
                else:
                    formatted_command = self.run.format(iteration)
                self.commands.append(
                    Command(
                        command=formatted_command,
                        working_dir=self._parse_cwd(),
                        return_code=self.success_code,
                        show_output=self.show_output,
                        env=self.env,
                    )
                )
        else:
            self.commands.append(
                Command(
                    command=self.run,
                    return_code=self.success_code,
                    working_dir=self._parse_cwd(),
                    show_output=self.show_output,
                    env=self.env,
                )
            )
        for index, command in enumerate(self.commands):
            self.commands[index].command = self.parse_variables_in_str(command.command)
        return len(self.commands)

    def _parse_each(self):
        """
        Parse the string under `each`, in case the command needs to iterate through a list.
        """
        if each := self.each:
            if isinstance(self.each, str):
                each = self.parse_variable(self.each)
                if not each:
                    self.error(f"Value for 'each' under {self.name} is not correct!", True)
            self.each = each

    def _parse_cwd(self) -> str:
        path = self.parse_variables_in_str(self.working_dir)
        path = Path(path).expanduser()
        if not path.exists() and not path.is_dir():
            raise TaskRunnerException(f"Working dir {self.working_dir} is not a valid directory!")
        return path.absolute().as_posix()

    def _parse_env(self) -> None:
        env = os.environ.copy()
        env.update({key: str(val) for key, val in self.env.items()} if self.env else {})
        self.env = env

    def _execute_commands(self) -> bool:
        # TODO - For some reason, commands are not empty when `run` is not set.
        if not self.commands:
            # Exit if we have nothing to run.
            return True
        TaskRunner.variables[f"{self.name}_output"] = ""
        for command in self.commands:
            command.execute()
            TaskRunner.variables[f"{self.name}_output"] += f"{command.output}\n"
            if isinstance(command.successful, bool) and not command.successful:
                logger.error(f"{command.command} failed:\n\t{command.error}")
            if self.check:
                self._check_output(command.output)
        all_successful = all(command.successful for command in self.commands)
        if not all_successful and not TaskRunner.dry_run:
            logger.error(f"{self.name} failed. See above for details.")
        return all_successful

    def describe_task(self) -> None:
        """
        Print out the task text, in case we're not in quiet mode.
        """
        if not TaskRunner.quiet:
            is_helper = isinstance(self, Helper)
            _color = color.YELLOW if is_helper else color.CYAN
            abrv = "HLP" if is_helper else "TSK"
            args = getattr(self, "_args", "")
            index = f"[{TaskRunner.current_task}/{len(TaskRunner.tasks)}]" if not is_helper else ""
            logger.info(f"{color.BOLD}{_color}{index} {abrv} {self.name}({args}){color.END}")
            if self.description:
                logger.info(self.description)

    def handle_input(self):
        """
        Get input from user with the given string.
        Store the input in `variables.<task_name>_input`.
        """
        if self.require_input:
            TaskRunner.variables[f"{self.name}_input"] = input(
                self.require_input if isinstance(self.require_input, str) else "Press ENTER to continue."
            ).rstrip()

    def error(self, message: str = "", fatal: bool = False):
        """
        Print an error message using `logger` with the task name as prefix.

        Args:
            message (str, optional): The error message. Defaults to "".
            fatal (bool, optional): Should we exit? Defaults to False.
        """
        logger.error(f"{self.name} - {message}")
        if fatal:
            exit(1)

    def parse_variable(self, _input: str):
        variable_pattern = r"(?:variables\.([a-zA-Z-9_]+))"
        match = re.findall(variable_pattern, _input)
        return TaskRunner.variables.get(match[0]) if match else None

    def parse_variables_in_str(self, _input: str | list) -> str | None:
        variable_pattern = r"(?:variables\.([a-zA-Z-9_]+))"
        if isinstance(_input, str):
            return re.sub(variable_pattern, self.get_variable, _input)
        elif isinstance(_input, list):
            for index, item in enumerate(_input):
                _input[index] = re.sub(variable_pattern, self.get_variable, item)
            return _input

    def get_variable(self, variable: str | re.Match):
        if isinstance(variable, re.Match):
            variable = variable.group(1)
        var = TaskRunner.variables.get(variable)
        if var is None:
            self.error(f"Variable {variable} doesn't exist!")
        return var

    def post_run(self) -> None:
        """
        Post run actions.
        """
        if self.on_failure or self.on_success:
            post_run_command: str | dict = getattr(self, "on_success" if self.success else "on_failure")
            if isinstance(post_run_command, str):
                logger.info(post_run_command)
                return
            if command := post_run_command.get("command", False):
                command = Command(command=command)
                command.execute()
            if message := post_run_command.get("message", False):
                logger.info(message)
            if skipto := post_run_command.get("skip_to", False):
                # TODO - Implement skip mechanism
                print(f"WOULD SKIP TO {skipto}")


@dataclass
class Task(Executable):
    prerequisites: str = ""
    check: str = ""
    show_output: bool = False
    output: list = field(default_factory=list)
    # """Store the command's output."""
    require_input: str | bool = False
    # """The message we should show, in case input is required. Display default message if True."""

    def _execute_task(self):
        self._parse_each()
        self._parse_env()
        self._populate_commands()
        self.describe_task()
        self.handle_input()
        self.success = self._execute_commands()
        self.post_run()
        if not self.success and not TaskRunner.dry_run:
            exit()

    def _check_output(self, output: str) -> bool:
        if self.check != "":
            rx = re.compile(self.check)
            logger.debug(f"Checking for {rx.pattern}")
            if not re.findall(rx, output):
                logger.error("Check Failed.")
                return False
        logger.debug(f'"{self.check}" is present in output')
        return True


@dataclass
class Helper(Task):
    _args: list = field(default_factory=list)


@dataclass
class Command:
    successful: None | bool = None
    command: str | list = ""
    working_dir: str = "."
    return_code: int = 0
    output: str = ""
    error: str = ""
    show_output: bool = False
    env: None | dict = None

    def __str__(self) -> str:
        return f"{self.command} (CWD: {self.working_dir}, Shell: {not isinstance(self.command, list)})"

    def execute(self):
        if TaskRunner.dry_run:
            logger.info(f"DRY RUN: {color.GRAY}{self}{color.END}")
            return False
        logger.debug(f"Executing {self}")
        proc = subprocess.Popen(
            self.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=not isinstance(self.command, list),
            cwd=self.working_dir,
            env=self.env,
        )
        while True:
            line: str = proc.stdout.readline().decode().rstrip()
            if line == "" and proc.poll() is not None:
                break
            self.output += line
            if self.show_output:
                logger.info(line)
            else:
                logger.debug(line)
        self.error = "\n".join(line.rstrip().decode() for line in proc.stderr.readlines())
        self.successful = self.return_code == proc.returncode

class TaskRunnerException(Exception):
    message: str
    
    def __init__(self, message = ""):
        self.message = message