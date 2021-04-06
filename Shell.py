"""Modul poskytující provizorní shellu
V nejbližší době se bude pořádně refraktorovat (tzn. že se celý modul přepíše), takže ani dokumentaci psát teď nehodlám
"""

from __future__ import annotations
#import abc
import re
import argparse

class ShellArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        #print(message, file=sys.stderr)
        print(message)
        self.print_help()
        raise ValueError()
    # def exit(self):
    #     pass

class Command:
    def __init__(self, name: str, callback, argparser: argparse.ArgumentParser = None, short_help: str = "", aliases: list[str] = [], spread_arguments = False):
        self.name: str = name
        self.argparser: argparse.ArgumentParser = argparser
        if self.argparser != None:
            self.argparser.prog = name
        self.callback = callback #Passing dict with values from Argparser
        self.short_help: str = short_help
        self.aliases: list[str] = aliases
        self.SPREAD_ARGUMENTS = spread_arguments

    # def Invoke(self, argumentList: list):
    #     self(*argumentList)
    def __call__(self, *args):
        if self.argparser is None:
            self.callback()
        else:
            try:
                try:
                    parsed = self.argparser.parse_args(args)
                except SystemExit: # Because when -h or --help is present, Argument parser (tries to) exit program
                    return
            except ValueError: # Because when parser fails it raise ValueError (and if not catched)
                pass
            else:
                if self.SPREAD_ARGUMENTS:
                    self.callback(**parsed.__dict__)
                else:
                    self.callback(parsed)

class Shell:
    Regex: re.Pattern = re.compile(r"(?<=\s)(?:((?:(?<!\\)\".+?(?<!\\)\")|(?:(?<!\\)'.+?(?<!\\)'))|((?:.(?<!\s))+?))(?=\s|$)")

    def __init__(
            self,
            *,
            prompt: str = "> ",
            commands: list[Command] = [],
            generate_commands: list[str] = ["help", "prompt", "exit"],
            first_command_case_sensitive: bool = False,
            allow_shorhands: bool = True,
            allow_python_exec: bool = False,
            python_exec_prefix: str = None,
            python_exec_globals: dict = {},
            python_exec_locals: dict = {},
            exit_on_ctrlc: bool = True,
            raise_on_ctrlc: bool = False,
            ):
        self.prompt: str = prompt
        self.commands: dict[str, Command] = {}

        self.FIRST_COMMAND_CASE_SENSITIVE: bool = first_command_case_sensitive
        self.ALLOW_SHORTHANDS: bool = allow_shorhands
        self.ALLOW_PYTHON_EXEC: bool = allow_python_exec
        self.PYTHON_EXEC_PREFIX: str = python_exec_prefix
        self.PYTHON_EXEC_GLOBALS: dict = python_exec_globals
        self.PYTHON_EXEC_LOCALS: dict = python_exec_locals
        self.EXIT_ON_CTRL_C: bool = exit_on_ctrlc
        self.RAISE_ON_CTRL_C: bool = raise_on_ctrlc

        self.should_exit: bool = False

        for command in commands:
            self.add_command(command)

        if generate_commands is None:
            generate_commands = []

        for command in generate_commands:
            if command == "help" or command == "?":
                self.add_command(Command(
                    "help",
                    self.print_help,
                    None,
                    "Zobrazí nápovědu",
                    ["?"]
                ))
            elif command == "prompt":
                parser = ShellArgumentParser()
                parser.add_argument(
                    "text",
                    help="Nový prompt text"
                )
                self.add_command(
                    Command(
                        "prompt",
                        self.change_prompt,
                        parser,
                        "Změní prompt text",
                        spread_arguments=True
                    )
                )
            elif command == "exit":
                self.add_command(Command(
                    "exit",
                    self.exit_loop,
                    None,
                    "Ukončí shell"
                ))
            # else:
            #     raise Exception("Unknown command to generate")

    def add_command(self, command: Command):
        self.commands[command.name if self.FIRST_COMMAND_CASE_SENSITIVE else command.name.lower()] = command
        # for alias in command.aliases:
        #     self.Commands[alias if self.FIRST_COMMAND_CASE_SENSITIVE else alias.lower()] = command

    def proc_string(self, string: str):
        if self.ALLOW_PYTHON_EXEC and self.PYTHON_EXEC_PREFIX is not None and string.startswith(self.PYTHON_EXEC_PREFIX):
            print(python_exec(string[len(self.PYTHON_EXEC_PREFIX):], self.PYTHON_EXEC_GLOBALS, self.PYTHON_EXEC_LOCALS))
            return
        parsed = self.parse_line(string)
        if len(parsed) == 0:
            return
        first = parsed.pop(0)
        if not self.FIRST_COMMAND_CASE_SENSITIVE:
            first = first.lower()
        if not self.ALLOW_SHORTHANDS:
            if first in self.commands:
                self.commands[first](*parsed)
            else:
                if self.ALLOW_PYTHON_EXEC and self.PYTHON_EXEC_PREFIX is None:
                    print(python_exec(string, self.PYTHON_EXEC_GLOBALS, self.PYTHON_EXEC_LOCALS))
                else:
                    print(f"Neznámý příkaz '{string}'\nZkus napsat 'help' nebo '?' pro nápovědu")
        else:
            full_match = None
            candidates = [] #TODO: Pokud má příkaz alias, tak může kovliktovat sám se sebou
            for _, command in self.commands.items():
                for command_name in [command.name] + command.aliases:
                    if command_name.startswith(first):
                        if len(first) == len(command_name):
                            full_match = command
                            break
                        candidates.append(command)
            if full_match is not None:
                full_match(*parsed)
            else:
                candidates_count = len(candidates)
                if candidates_count == 0:
                    if self.ALLOW_PYTHON_EXEC and self.PYTHON_EXEC_PREFIX is None:
                        print(python_exec(string, self.PYTHON_EXEC_GLOBALS, self.PYTHON_EXEC_LOCALS))
                    else:
                        print(f"Neznámý příkaz '{string}'\nZkus napsat 'help' nebo '?' pro nápovědu")
                elif candidates_count == 1:
                    candidates[0](*parsed)
                else:
                    print("Nejednoznačný příkaz; Možní kándidáti:")
                    for candidate in candidates:
                        print("%-20s %s" % (candidate.name, candidate.short_help))

    def print_help(self):
        print("Možné příkazy:")
        for _, command in self.commands.items():
            print("\t%-25s - %s" % (" | ".join([command.name] + command.aliases), command.short_help))
        if self.ALLOW_PYTHON_EXEC:
            if self.PYTHON_EXEC_PREFIX is None:
                print("Jakýkoli příkaz (/vstup), který nebude rozeznán, bude interpretován jakožto Python")
            else:
                print(f"Jakýkoli příkaz (/vstup), který má na začátku '{self.PYTHON_EXEC_PREFIX}', bude interpretován jakožto Python")
    def change_prompt(self, text: str):
        self.prompt = text

    def start_loop(self):
        try:
            while True:
                if self.should_exit: # If something requested exit, exit
                    return
                inpt = input(self.prompt)
                if self.should_exit: # If something requested exit but we are alredy asked user for input, exit here to prevent executing next command
                    return
                if inpt != "":
                    self.proc_string(inpt)
        except KeyboardInterrupt:
            if self.RAISE_ON_CTRL_C:
                raise KeyboardInterrupt
            if self.EXIT_ON_CTRL_C:
                self.should_exit = True

    def exit_loop(self): #TODO: Try find a way how to "terminate" input function (or do custom input system (by recording keys and have buffer for it)). Maybe we could raise some exception?
        self.should_exit = True

    def parse_line(self, line: str) -> list[str]:
        parsed = []
        regex_split = self.Regex.findall(" " + line) #Mezera před stringem, protože python regex engine nepodporuje začátek stringu v look-behind (resp. variabilní délku look-behind(u))
        for part in regex_split:
            parsed.append(part[1] if part[0] == "" else part[0][1:-1])
        return parsed

def python_exec(string: str, globals_ = {}, locals_ = {}):
    #TODO: Better python_exec() output
    try:
        return eval(string, globals_, locals_)
    except Exception as e:
        print(e)
