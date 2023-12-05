from abc import ABC
from dataclasses import dataclass, field, replace
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import List, Dict
from taskrunner import __version__
from datetime import datetime

from collections import ChainMap

import logging
import yaml

logger = logging.getLogger(__name__)


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
    tasks: List["Task"] = []
    variables: dict = {}
    helpers: Dict[str, "Helper"] = {}

    def __init__(
        self, task_file: str, quiet: bool, dry_run: bool, text_only: bool
    ) -> None:
        self._decide_logger_format()
        TaskRunner.quiet = quiet
        TaskRunner.dry_run = dry_run
        TaskRunner.text_only = text_only
        task_path = Path(task_file)
        if not task_path.exists():
            logger.error(f"{task_path} doesn't exist. Aborting!")
            exit(1)
        self.task_path = task_path

    def _decide_logger_format(self):
        if logger.getEffectiveLevel() >= 20:
            format = "%(message)s"
        else:
            format = "%(levelname)-8s - %(funcName)s - %(message)s"
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=format)

    def _parse_taskfile(self) -> bool:
        """Load the YAML file and parse the sections within."""
        parsed_yaml = yaml.safe_load(self.task_path.open(encoding="UTF-8"))
        if "information" in parsed_yaml:
            if isinstance(parsed_yaml["information"], str):
                logger.info(f"Information: {parsed_yaml['information'].strip()}")
        if "variables" in parsed_yaml:
            self._populate_variables(parsed_yaml["variables"])
        if "helpers" in parsed_yaml:
            self._populate_helpers(parsed_yaml["helpers"])
        if "tasks" in parsed_yaml:
            self._populate_tasks(parsed_yaml["tasks"])
        return parsed_yaml

    def _populate_tasks(self, tasks: list):
        logger.info(f"Tasks: {color.BOLD}{len(tasks)}{color.END}")
        for name, config in tasks.items():
            self.tasks.append(Task(name=name, **config))
            logger.debug(f"Task {name} added.")
        pass

    def _populate_variables(self, variables: List[dict]):
        logger.info(f"Variables: {color.BOLD}{len(variables)}{color.END}")
        for name, value in ChainMap(*variables).items():
            self.variables[name] = value
            logger.debug(f"Variable {name} added.")

    def _populate_helpers(self, helpers: list):
        logger.info(f"Helpers: {color.BOLD}{len(helpers)}{color.END}")
        for name, config in helpers.items():
            self.helpers[name] = Helper(name=name, **config)
            logger.debug(f"Helper {name} added.")

    # def _get_variable(self, variable):
    #     # print(self.variables.get(variable.group(1), ""))
    #     return self.variables.get(variable.group(1), "")

    # def _parse_variables_in_command(self, command: str):
    #     variable_pattern = r"(?:{(.*?)})"
    #     return re.sub(variable_pattern, self._get_variable, command)

    def _parse_each_loop(self, items: str | list) -> list:
        if isinstance(items, str):
            var = self._parse_variables_in_command(items)
            return self._get_variable(var)
        return items

    def _get_prerequisite(self, prerequisite: str):
        pass

    def _parse_prerequisites_in_task(self, prerequisites: str):
        prerequisite_list = prerequisites.split(" ") if prerequisites != "" else []
        for i, prerequisite in enumerate(prerequisite_list):
            if prerequisite.startswith("helpers"):
                helper_pattern = r"(?:helpers\.)(\w+)(?:\((.*?)\))?"
                helper, _args = re.findall(helper_pattern, prerequisite)[0]
                if _helper := self.helpers.get(helper):
                    prerequisite_list[i] = replace(_helper)
                    prerequisite_list[i]._args = _args.split()
        return prerequisite_list

    def run(self):
        if TaskRunner.quiet:
            logger.setLevel(logging.ERROR)
        logger.info(
            f"{color.BOLD}{color.DARKCYAN}[TaskRunner {__version__}]{color.END}"
        )
        logger.info(f"Task File: {color.BOLD}{self.task_path.absolute()}{color.END}")
        if TaskRunner.dry_run:
            logger.info(f"Dry Run: {color.BOLD}True{color.END}")
        self._parse_taskfile()
        logger.info("---")
        logger.info(f"Started: {color.BOLD}{datetime.today()}{color.END}")
        for task in self.tasks:
            prerequisites = self._parse_prerequisites_in_task(task.prerequisites)
            for prerequsite in prerequisites:
                if not isinstance(prerequsite, Helper):
                    continue
                if not prerequsite._run():
                    prerequsite.error(
                        f"Stopping because prerequisite {prerequsite.name} failed.",
                        fatal=True,
                    )
            task._run()
        logger.info(f"Ended: {color.BOLD}{datetime.today()}{color.END}")


class Executable(ABC):
    name: str
    text: str = ""
    run: str = ""
    each: list = []

    def _orun(self):
        """
        Parse the string under `each`, in case the command needs to iterate through a list.
        """
        # FIXME - Temporary function name to handle the `each` cycle.
        # TODO - Consider setting `self.commands` directly from here.
        if each := getattr(self, "each"):
            if isinstance(self.each, str):
                each = self.parse_variable(self.each)
                if not each:
                    self.error(
                        f"Value for 'each' under {self.name} is not correct!", True
                    )
            self.each = each

    def announce(self):
        """
        Print out the task text, in case we're not in quiet mode.
        """
        # FIXME - Add check for text only mode as well.
        if not TaskRunner.quiet and self.text:
            logger.info(
                f"{color.UNDERLINE}{self.__class__.__name__} {self.name}{color.END} - {self.text}"
            )

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


@dataclass
class Task(Executable):
    name: str
    text: str = ""
    run: list | str = ""
    """The command this task needs to run. `str` for shell, `list` for no shell."""
    commands: list = field(default_factory=list)
    each: str | list = field(default_factory=list)
    prerequisites: str = ""
    prerequisite_list: list = field(default_factory=list)
    check: str = ""
    success: int = 0
    cwd: str = os.getcwd()
    env: bool = False
    show_output: bool = False
    output: list = field(default_factory=list)
    """Store the command's output."""
    require_input: str | bool = False
    """The message we should show, in case input is required. Display default message if True."""
    user_input: str = ""
    """Store user input result from `require_input`."""
    on_failure: str = ""
    on_success: str = ""

    def _run(self):
        self._orun()  # FIXME - Temporary
        logger.debug(f"Starting task {self.name}")
        if self.each:
            for iteration in self.each:
                formatted_command = self.run.format(iteration)
                self.commands.append(formatted_command)
        else:
            self.commands = [self.run]
        self.announce()
        if self.require_input:
            TaskRunner.variables[f"{self.name}_input"] = input(
                self.require_input
                if isinstance(self.require_input, str)
                else "Press ENTER to continue."
            )
        if not self.run:
            # NOTE - Stop if there's nothing to run
            return
        for command in self.commands:
            self.cwd = Path(self.cwd).expanduser()
            shell = not isinstance(command, list)
            command = self.parse_variables_in_str(command)
            # FIXME - Take into account `run` can be a list, so go over list items to format them.
            run_message = f"(Shell: {shell}, CWD: {self.cwd}): {command}"
            if TaskRunner.dry_run:
                logger.info(f"{color.GRAY}DRY RUN {run_message}{color.END}")
                return True
            else:
                logger.debug(f"Running {run_message}")
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=shell,
                cwd=self.cwd,
                env=os.environ if self.env else None,
            )
            while True:
                line: str = proc.stdout.readline().decode().rstrip()
                if line == "" and proc.poll() is not None:
                    break
                self.output.append(line)
                if self.show_output:
                    logger.info(line)
                else:
                    logger.debug(line)
            # logger.debug(proc.stdout.decode())
            TaskRunner.variables[f"{self.name}_output"] = "\n".join(self.output)
            self._check_output()
            if not proc.returncode == self.success:
                error = "\n".join(
                    line.rstrip().decode() for line in proc.stderr.readlines()
                )
                logger.error(f'Command "{command}" failed ({proc.returncode}): {error}')
        return proc.returncode == self.success

    def _check_output(self) -> bool:
        command_output = "\n".join(self.output)
        if self.check != "":
            rx = re.compile(self.check)
            logger.debug(f"Checking for {rx.pattern}")
            if not re.findall(rx, command_output):
                logger.error("Check Failed.")
                return False
        logger.debug(f'"{self.check}" is present in output')
        return True


@dataclass
class Helper(Executable):
    name: str
    run: str = ""
    text: str = ""
    _args: list = field(default_factory=list)
    shell: bool = False
    success: int = 0

    def _run(self) -> bool:
        logger.debug(f"Starting helper {self.name}")
        self.announce()
        command = self.run.format(*self._args)
        command = command if self.shell else command.split(" ")
        run_message = f"(Shell: {self.shell}): {command}"
        if TaskRunner.dry_run:
            logger.info(f"{color.GRAY}DRY RUN {run_message}{color.END}")
            return True
        else:
            logger.debug(f"Running {run_message}")
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=self.shell,
        )
        if proc.returncode == self.success:
            return True
        logger.error(
            f"{self.name} failed with {proc.returncode}: {proc.stdout.decode()}"
        )
        return False
        # print(proc.stderr)

    def _announce_helper(self):
        if TaskRunner.quiet:
            return
        logger.info(f"Prerequisite {self.name} - {self.text}")
