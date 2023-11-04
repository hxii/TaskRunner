import copy
from dataclasses import dataclass, field, replace
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import List, Dict

# from pprint import pprint as print #TODO: Remove
from collections import ChainMap
from termcolor import colored

import logging
import yaml

logger = logging.getLogger(__name__)
# logging.basicConfig(stream=sys.stdout, level=logging.INFO)
# logger.setLevel(logging.DEBUG)


class TaskRunner:

    quiet: bool = False

    def __init__(self, task_file: str, quiet: bool = False) -> None:
        self.quiet = quiet
        self._decide_logger_format()
        logger.info(f"TaskRunner Initialized with file {task_file}")
        task_path = Path(task_file)
        if not task_path.exists():
            logger.error(f"{task_file} doesn't exist. Aborting!")
            exit(1)
        self.task_path = task_path
        self.tasks: List["Task"] = []
        self.variables: dict = {}
        self.helpers: Dict[str, "Task"] = {}
        self._parse_taskfile()

    def _decide_logger_format(self):
        if logger.getEffectiveLevel() >= 20:
            format = "%(message)s"
        else:
            format = "%(levelname)-8s - %(funcName)s - %(message)s"
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=format)

    def _parse_taskfile(self) -> bool:
        """Load the YAML file and parse the sections within."""
        parsed_yaml = yaml.safe_load(self.task_path.open(encoding="UTF-8"))
        if "variables" in parsed_yaml:
            self._populate_variables(parsed_yaml["variables"])
        if "helpers" in parsed_yaml:
            self._populate_helpers(parsed_yaml["helpers"])
        if "tasks" in parsed_yaml:
            self._populate_tasks(parsed_yaml["tasks"])
        return parsed_yaml

    def _populate_tasks(self, tasks: list):
        logger.info(f"{len(tasks)} Task(s) found. Populating...")
        for name, config in tasks.items():
            task = Task(name=name, **config)
            task.command = self._parse_variables_in_command(task.command)
            print(task.command)
            task.prerequisite_list = self._parse_prerequisites_in_task(
                task.prerequisites
            )
            self.tasks.append(task)
            logger.debug(f"Task {name} added.")
        pass

    def _populate_variables(self, variables: List[dict]):
        logger.info(f"{len(variables)} Variable(s) found. Populating...")
        for name, value in ChainMap(*variables).items():
            self.variables[name] = value.rstrip()
            logger.debug(f"Variable {name} added.")

    def _populate_helpers(self, helpers: list):
        logger.info(f"{len(helpers)} Helper(s) found. Populating...")
        for name, config in helpers.items():
            self.helpers[name] = Helper(name=name, **config)
            logger.debug(f"Helper {name} added.")

    def _get_variable(self, variable: re.Match) -> str:
        print(self.variables.get(variable.group(1), ""))
        return self.variables.get(variable.group(1), "")

    def _parse_variables_in_command(self, command: str):
        variable_pattern = r"(?:{(.*?)})"
        return re.sub(variable_pattern, self._get_variable, command)

    def _get_prerequisite(self, prerequisite: str):
        pass

    def _parse_prerequisites_in_task(self, prerequisites: str):
        prerequisite_list = prerequisites.split(" ")
        for i, prerequisite in enumerate(prerequisite_list):
            if prerequisite.startswith("helpers"):
                helper_pattern = r"(?:helpers\.)(\w+)(?:\((.*?)\))?"
                helper, _args = re.findall(helper_pattern, prerequisite)[0]
                if _helper := self.helpers.get(helper):
                    prerequisite_list[i] = replace(_helper)
                    prerequisite_list[i]._args = _args.split()
        return prerequisite_list

    def run(self):
        logger.info("Start running tasks...")
        for task in self.tasks:
            task.run()


@dataclass
class Task:
    name: str
    command: str = ""
    text: str = ""
    prerequisites: str = ""
    prerequisite_list: list = field(default_factory=list)
    check: str = ""
    success: int = 0
    shell: bool = False
    cwd: str = os.getcwd()
    env: bool = False

    def run(self):
        logger.debug(f"Starting task {self.name}")
        self.stdout = ""
        self._announce_task()
        if self.prerequisite_list[0] != "":
            logger.debug(f"Task has {len(self.prerequisite_list)} prerequisite(s)")
            for prerequisite in self.prerequisite_list:
                if not prerequisite.run():
                    exit(f"Prerequisite {prerequisite.name} failed!")
        if not self.command:
            return
        command = self.command if self.shell else self.command.split(" ")
        self.cwd = Path(self.cwd).expanduser()
        logger.debug(f"Running (Shell: {self.shell}, CWD: {self.cwd}): {command}")
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=self.shell,
            cwd=self.cwd,
            env=os.environ if self.env else None,
        )
        from pprint import pprint

        pprint(proc.stdout.decode())
        # for line in iter(proc.stdout.readline, b''):
        #     logger.debug(line.decode())
        #     self.stdout += line.decode()
        self._check_output(proc.stdout.decode())
        return proc.returncode == self.success

    def _announce_task(self):
        """Print out task's text, unless quiet has been set."""
        if TaskRunner.quiet:
            return
        logger.info(f"Task {self.name} - {self.text}")

    def _check_output(self, output) -> bool:
        if self.check != "":
            rx = re.compile(self.check)
            if not re.findall(rx, output):
                logger.error("Check Failed.")
                return False
        logger.debug(f'"{self.check}" is present in output')
        return True


@dataclass
class Helper:
    name: str
    command: str = ""
    text: str = ""
    _args: list = field(default_factory=list)
    shell: bool = False

    def run(self) -> bool:
        logger.debug(f"Starting helper {self.name}")
        self._announce_helper()
        command = self.command.format(*self._args)
        command = command if self.shell else command.split(" ")
        logger.debug(f"Running helper {command}")
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            shell=self.shell,
        )
        # for line in iter(proc.stdout.readline, b''):
        #     logger.debug(line)
        # proc.stdout.close()
        if proc.returncode == 0:
            return True
        logger.error(f"{self.name} failed with {proc.returncode}")
        print(proc.stderr)

    def _announce_helper(self):
        if TaskRunner.quiet:
            return
        logger.info(f"Prerequisite {self.name} - {self.text}")
