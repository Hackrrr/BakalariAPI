"""Modulární shell pro Python"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import shlex
import sys
from enum import Enum, IntEnum
from typing import Any, Callable, Iterable

from rich import console, traceback, print as rich_print

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import DummyHistory
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.output.vt100 import Vt100_Output
from prompt_toolkit.patch_stdout import patch_stdout

__all__ = [
    "ShellArgumentParser",
    "Command",
    "ShellPredefinedCommands",
    "Shell",
]


def cls():
    os.system("cls" if os.name == "nt" else "clear")


def restart():
    """Restartuje program.

    Pokud se této funkci podaří program restartovat, nenavrátí se.
    Pokud se restart nepodaří, funkce se vrátí.

    Pozn.:
        Pokud se restatartuje program, který byl spuštěn skrze CMD, tak
        se může stát, že se program spustí, ale bude zakryt samotným CMD.
        Aby se teda uživatel dostal do restartovaného programu, musí se
        dostat pryč z CMD, tedy příkaz `exit`.
        Pokud se program restartuje podruhé, tedy potom, co se již vyskočilo
        z CMD, tak vše proběhne normálně.

        Proč je restartovaný program zakrytí CMDčkem? Nemám tušení.
        Ale tipl bych si, že se to má co dělat se "sdíleným" stdin(em).

        Proč při druhém restartu problém už není?
        Jelikož po prvním restartu zavřeme CMD, tak logicky už neběží a tím
        pádem se toto stát nemůže.
    """
    if sys.executable is None:
        print("Unable to restart due to unknown iterpreter")
        return
    cls()  # Aby se člověk neztratil v záplavě textu
    os.execvp(sys.executable, ["python"] + sys.argv)


class ShellArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(message)
        self.print_help()
        raise ValueError()


class Command:
    def __init__(
        self,
        name: str,
        callback: Callable,
        *,
        argparser: argparse.ArgumentParser = None,
        short_help: str = "",
        aliases: list[str] | None = None,
        spread_arguments: bool = True,
    ):
        self.name: str = name
        self.argparser: argparse.ArgumentParser = (
            ShellArgumentParser() if argparser is None else argparser
        )
        self.argparser.prog = name
        self.callback = callback  # Passing dict with values from Argparser
        self.short_help: str = short_help
        self.aliases: list[str] = [] if aliases is None else aliases
        self.SPREAD_ARGUMENTS: bool = spread_arguments

        if self.argparser.description is None:
            self.argparser.description = short_help

    def __call__(self, args: list[str], name: str = ""):
        if name:
            self.argparser.prog = name
        try:
            parsed = vars(self.argparser.parse_args(args))
        except SystemExit:  # Because when -h or --help is present, Argument parser (tries to) exit program
            return
        except ValueError:  # Because when parser fails it raise ValueError
            pass
        else:
            if self.SPREAD_ARGUMENTS:
                self.callback(**parsed)
            else:
                self.callback(parsed)
        finally:
            self.argparser.prog = self.name


class ShellCompleter(Completer):
    def __init__(self, shell: Shell):
        self.shell = shell

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        for priority, entries_by_priority in self.shell.commands.items():
            prev_word_pos = document.find_previous_word_beginning()
            if (prev_word_pos is None and document.cursor_position != 0) or (
                prev_word_pos is not None
                and document.cursor_position + prev_word_pos != 0
            ):
                return []
            for entry in entries_by_priority:
                if entry.startswith(document.text):
                    yield Completion(
                        entry,
                        start_position=0 if prev_word_pos is None else prev_word_pos,
                        style={
                            CommandEntryPriority.BASE: "",
                            CommandEntryPriority.ALIAS: "bg:ansibrightyellow",
                            CommandEntryPriority.USER_ALIAS: "bg:ansibrightyellow",
                        }[priority],
                        selected_style={
                            CommandEntryPriority.BASE: "",
                            CommandEntryPriority.ALIAS: "bg:ansiyellow",
                            CommandEntryPriority.USER_ALIAS: "bg:ansiyellow",
                        }[priority],
                    )


class CandidateMatchPriority(IntEnum):
    FULL = 0
    FULL_ALIAS = 1
    SHORTHAND = 2
    SHORTHAND_ALIAS = 3


class CandidateMatch:
    def __init__(
        self,
        command: Command,
        priority: CandidateMatchPriority,
        named_as: str | None = None,
    ):
        self.command: Command = command
        self.priority: CandidateMatchPriority = priority
        self.named_as: str = command.name if named_as is None else named_as


class CommandEntryPriority(IntEnum):
    BASE = 0
    ALIAS = 1
    USER_ALIAS = 2


class CommandEntry:
    def __init__(self, name: str, command: Command, priority: CommandEntryPriority):
        self.name: str = name
        self.command: Command = command
        self.priority: CommandEntryPriority = priority


class ShellPredefinedCommands(Enum):
    EXIT = "exit"
    HELP = "help"
    PROMPT = "prompt"
    ALIAS = "alias"
    CLEAR = "clear"
    RESTART = "restart"


class Shell:
    def __init__(
        self,
        *,
        prompt: str = "> ",
        commands: list[Command] | None = None,
        predefined_commands: list[ShellPredefinedCommands] = [
            x for x in ShellPredefinedCommands
        ],
        first_command_case_sensitive: bool = False,
        allow_shorhands: bool = True,
        allow_python_exec: bool = False,
        python_exec_prefix: str = None,
        python_exec_globals: dict[str, Any] | None = None,
        python_exec_locals: dict[str, Any] | None = None,
        end_on_ctrlc: bool = True,
        raise_on_ctrlc: bool = False,
        command_exception_traceback: bool = True,
        command_exception_traceback_locals: bool = False,
        command_exception_reraise: bool = True,
        history: bool = True,
        history_suggestions: bool = True,
        autocomplete: bool = True,
        completely_disable_bell: bool = True,
        enable_copy: bool = True,  # TODO: Make this work
        enable_paste: bool = True,  # TODO: Make this work,
        rich_prompt: bool = False,
    ):
        self.prompt: str = prompt
        self.commands: dict[CommandEntryPriority, dict[str, CommandEntry]] = {
            x: {} for x in [y for y in CommandEntryPriority]
        }

        self.FIRST_COMMAND_CASE_SENSITIVE: bool = first_command_case_sensitive
        self.ALLOW_SHORTHANDS: bool = allow_shorhands
        self.ALLOW_PYTHON_EXEC: bool = allow_python_exec
        self.PYTHON_EXEC_PREFIX: str | None = python_exec_prefix
        self.PYTHON_EXEC_GLOBALS: dict[str, Any] = (
            {} if python_exec_globals is None else python_exec_globals
        )
        self.PYTHON_EXEC_LOCALS: dict[str, Any] = (
            {} if python_exec_locals is None else python_exec_locals
        )
        self.END_ON_CTRL_C: bool = end_on_ctrlc
        self.RAISE_ON_CTRL_C: bool = raise_on_ctrlc
        self.COMMAND_EXCEPTION_TRACEBACK: bool = command_exception_traceback
        self.COMMAND_EXCEPTION_TRACEBACK_LOCALS: bool = (
            command_exception_traceback_locals
        )
        self.COMMAND_EXCEPTION_RERAISE: bool = command_exception_reraise
        self.RICH_PROMPT: bool = rich_prompt

        if completely_disable_bell:
            # `prompt_toolkit` je super, ale někdo dostal skvělý nápad implementovat v základu zvuk bez možnosti vypnutí...
            # Tím pádem si ho vypneme sami :)
            setattr(Vt100_Output, "bell", lambda _: None)
            # Pozn.: Ono to jde vypnout asi i nějak "normálně" (resp. normálněji), ale to se mi nechce řešit.
            # Vt100_Output má totiž jako parametr "enable_bell", kterým se vlastně dá disablovat bell funkce,
            # ale problém je ten, že bychom museli tedy vytvořit vlastní Vt100_Output instanci - A já nevím,
            # co za parametry tam ještě musí být, aby to fungovalo tak jak má eShrug (A navíc je dost možný
            # že se tím nějak úplně zničí terminál)

        bindings = KeyBindings()
        if enable_paste:

            @bindings.add("c-v")
            def _(event: KeyPressEvent):
                # event.current_buffer.document.paste_clipboard_data()
                ...

        self._promt_session = PromptSession(
            history=None if history else DummyHistory(),
            auto_suggest=AutoSuggestFromHistory() if history_suggestions else None,
            completer=ShellCompleter(self) if autocomplete else None,
            # complete_while_typing=False
        )

        self._should_exit: bool = False
        self._running: bool = False

        if commands is not None:
            for command in commands:
                self.add_command(command)

        for predefined_command in predefined_commands:
            if predefined_command == ShellPredefinedCommands.EXIT:
                self.add_command(
                    Command("exit", self.stop_loop, short_help="Ukončí shell")
                )
            elif predefined_command == ShellPredefinedCommands.HELP:
                self.add_command(
                    Command(
                        "help",
                        self.print_help,
                        short_help="Zobrazí nápovědu",
                        aliases=["?", "napoveda"],
                    )
                )
            elif predefined_command == ShellPredefinedCommands.PROMPT:
                parser = ShellArgumentParser()
                parser.add_argument("text", help="Nový prompt text")
                self.add_command(
                    Command(
                        "prompt",
                        self.change_prompt,
                        argparser=parser,
                        short_help="Změní prompt text",
                        spread_arguments=True,
                    )
                )
            elif predefined_command == ShellPredefinedCommands.ALIAS:
                parser = ShellArgumentParser()
                subparsers = parser.add_subparsers(
                    required=True,
                    metavar="příkaz",
                    dest="cmd",
                    parser_class=ShellArgumentParser,
                )

                # add
                parser_add = subparsers.add_parser(
                    "add",
                    help="Přidá nový alias",
                )
                parser_add.add_argument(
                    metavar="nazev", help="Název pro nový alias", dest="alias"
                )
                parser_add.add_argument(
                    metavar="prikaz",
                    help="Příkaz, který bude zastupován novým aliasem",
                    dest="command",
                )

                # list
                parser_list = subparsers.add_parser(
                    "list",
                    help="Vypíše všechny uživatelky vytvořené aliasy",
                )

                # delete
                parser_delete = subparsers.add_parser(
                    "delete",
                    help="Odstraní uživatelsky vytvořený alias",
                )
                parser_delete.add_argument(
                    "alias", help="Název aliasu, který se má smazat"
                )

                self.add_command(
                    Command(
                        "alias",
                        self.__alias_command_handler,
                        argparser=parser,
                        short_help="Vytvoří alias",
                        spread_arguments=False,
                    )
                )
            elif predefined_command == ShellPredefinedCommands.CLEAR:
                self.add_command(
                    Command(
                        "clear",
                        cls,
                        short_help="Vyčistí konzoli/terminál",
                        aliases=["cls"],
                    )
                )
            elif predefined_command == ShellPredefinedCommands.RESTART:
                self.add_command(
                    Command(
                        "restart",
                        restart,
                        short_help="Restartuje program",
                        argparser=ShellArgumentParser(
                            description="Restartuje program\nPozn.: Pokud je program spuštěn v systému Windows přes CMD, může se při prvním restartu stát, že program 'dropne' do CMD zatímco stále běží. V tom případě stačí vyskočit z CMD."
                        ),
                    )
                )

    def add_command(self, command: Command):
        self.add_command_entry(
            CommandEntry(
                command.name
                if self.FIRST_COMMAND_CASE_SENSITIVE
                else command.name.lower(),
                command,
                CommandEntryPriority.BASE,
            )
        )
        for alias in command.aliases:
            self.add_command_entry(
                CommandEntry(
                    alias if self.FIRST_COMMAND_CASE_SENSITIVE else alias.lower(),
                    command,
                    CommandEntryPriority.ALIAS,
                )
            )

    def add_command_entry(self, entry: CommandEntry):
        self.commands[entry.priority][entry.name] = entry
        if self._running:
            self._sort_commands(entry.priority)

    def _sort_commands(self, priority: CommandEntryPriority | None = None):
        # Pravděpodobně moc efektivní není, ale alespoň by to mělo být seřazený
        for priority in self.commands.keys() if priority is None else [priority]:
            self.commands[priority] = {
                k: v for k, v in sorted(self.commands[priority].items())
            }

    def proc_string(self, inpt: str):

        # Pokud máme povolen PYTHON_EXEC a input začíná PYTHON_EXEC prefixem (teda pokud máme prefix pro PYTHON_EXEC), tak...
        if (
            self.ALLOW_PYTHON_EXEC
            and self.PYTHON_EXEC_PREFIX is not None
            and inpt.startswith(self.PYTHON_EXEC_PREFIX)
        ):
            # ... spoustíme PYTHON_EXEC a vrátíme se, ...
            self.__python_exec(inpt[len(self.PYTHON_EXEC_PREFIX) :])
            return
        # ... jinak jdeme dál

        parsed = self.parse_line(inpt, True)
        if len(parsed) == 0:
            return

        # `parse_line` vrací list[list[str]], protože podporuje ";" a tím pádem můžeme mít více příkazů v jednom
        for parsed_line in parsed:
            candidates: list[CandidateMatch] = []
            # Stačí nám porovnávat jen první slovo/část, jelikož zbytek případně obstarává argparse
            first_word = parsed_line.pop(0)
            if not self.FIRST_COMMAND_CASE_SENSITIVE:
                first_word = first_word.lower()

            # Nejdříve najdeme kandidáty
            if self.ALLOW_SHORTHANDS:
                first_word_length = len(first_word)
                for entries_priority, entries_by_priority in self.commands.items():
                    for command_name, command_entry in entries_by_priority.items():
                        if command_name.startswith(first_word):
                            if first_word_length == len(command_name):
                                candidates.append(
                                    CandidateMatch(
                                        command_entry.command,
                                        CandidateMatchPriority.FULL
                                        if entries_priority == CommandEntryPriority.BASE
                                        else CandidateMatchPriority.FULL_ALIAS,
                                        command_name,
                                    )
                                )
                                break
                            else:
                                candidates.append(
                                    CandidateMatch(
                                        command_entry.command,
                                        CandidateMatchPriority.SHORTHAND
                                        if entries_priority == CommandEntryPriority.BASE
                                        else CandidateMatchPriority.SHORTHAND_ALIAS,
                                        command_name,
                                    )
                                )
                            # Nemůžeme, protože chceme vyskočit, když nastane FULL match, což s tímhle syntaxem nelze
                            # candidates.append(CommandMatchCandidate(
                            #     command_entry.command,
                            #     (
                            #         CandidateMatchPriority.FULL
                            #         if entries_priority == CommandEntryPriority.BASE
                            #         else CandidateMatchPriority.FULL_ALIAS
                            #     ) if first_word_length == len(command_name) else (
                            #         CandidateMatchPriority.SHORTHAND
                            #         if entries_priority == CommandEntryPriority.BASE
                            #         else CandidateMatchPriority.SHORTHAND_ALIAS
                            #     ),
                            #     command_name
                            # ))
            else:
                for entries_priority, entries_by_priority in self.commands.items():
                    if first_word in entries_by_priority:
                        candidates.append(
                            CandidateMatch(
                                entries_by_priority[first_word].command,
                                CandidateMatchPriority.FULL
                                if entries_priority == CommandEntryPriority.BASE
                                else CandidateMatchPriority.FULL_ALIAS,
                                first_word,
                            )
                        )
                        break

            # A následně kandidáty zpracujeme
            candidates_length = len(candidates)
            if candidates_length == 0:
                if self.ALLOW_PYTHON_EXEC and self.PYTHON_EXEC_PREFIX is None:
                    self.__python_exec(inpt)
                else:
                    print(
                        f"Neznámý příkaz '{inpt}'\nMůžeš zkusit napsat 'help' nebo '?' pro nápovědu"
                    )
            elif candidates_length == 1:
                candidates[0].command(parsed_line, candidates[0].named_as)
            else:
                candidates_by_priority: dict[
                    CandidateMatchPriority, list[CandidateMatch]
                ] = {x: [] for x in [y for y in CandidateMatchPriority]}
                for candidate in candidates:
                    candidates_by_priority[candidate.priority].append(candidate)
                for candidate_priority, candidate_set in candidates_by_priority.items():
                    set_length = len(candidate_set)
                    if set_length == 0:
                        continue
                    else:
                        if set_length == 1:
                            candidate_set[0].command(
                                parsed_line, candidate_set[0].named_as
                            )
                        else:
                            candidate_level = {
                                CandidateMatchPriority.FULL: "plná shoda",
                                CandidateMatchPriority.FULL_ALIAS: "plná shoda aliasu",
                                CandidateMatchPriority.SHORTHAND: "počáteční shoda",
                                CandidateMatchPriority.SHORTHAND_ALIAS: "počáteční shoda aliasu",
                            }[candidate_priority]
                            print(f"Nejednoznačný příkaz: (úroveň: {candidate_level})")
                            for candidate in candidate_set:
                                print(
                                    "%-20s %s"
                                    % (candidate.named_as, candidate.command.short_help)
                                )
                        break
                # Pokud se kód dostane do této větve, tak vždy nějakého kandidáta máme, tudíž zde nemusíme mít (další) zprávu o neznámém příkazu

    def print_help(self):
        print("Možné příkazy:")
        for command_entry in self.commands[CommandEntryPriority.BASE].values():
            print(
                "\t%-25s - %s"
                % (
                    " | ".join(
                        [command_entry.command.name] + command_entry.command.aliases
                    ),
                    command_entry.command.short_help,
                )
            )

        if len(self.commands[CommandEntryPriority.USER_ALIAS]) != 0:
            print("Existují následující uživatelské aliasy:")
            for command_entry in self.commands[
                CommandEntryPriority.USER_ALIAS
            ].values():
                print(
                    "\t%-10s => %s" % (command_entry.name, command_entry.command.name)
                )

        if self.ALLOW_PYTHON_EXEC:
            if self.PYTHON_EXEC_PREFIX is None:
                print(
                    "Jakýkoli příkaz (/vstup), který nebude rozeznán, bude interpretován jakožto Python"
                )
            else:
                print(
                    f"Jakýkoli příkaz (/vstup), který má na začátku '{self.PYTHON_EXEC_PREFIX}', bude interpretován jakožto Python"
                )

    def change_prompt(self, text: str):
        self.prompt = text

    def __alias_command_handler(self, namespace: dict[str, Any]):
        cmd = namespace["cmd"]
        if cmd == "add":
            self.add_command_entry(
                CommandEntry(
                    namespace["alias"],
                    Command(
                        namespace["command"],
                        lambda _: self.proc_string(namespace["command"]),
                        spread_arguments=False,
                    ),
                    CommandEntryPriority.USER_ALIAS,
                )
            )
        elif cmd == "list":
            print("Uživatelké aliasy:")
            for command_entry in self.commands[
                CommandEntryPriority.USER_ALIAS
            ].values():
                print(
                    "\t%-10s => %s" % (command_entry.name, command_entry.command.name)
                )
        elif cmd == "delete":
            try:
                del self.commands[CommandEntryPriority.USER_ALIAS][namespace["alias"]]
            except KeyError:
                print(f"Alias '{namespace['alias']}' nenalezen")
            else:
                print(f"Alias '{namespace['alias']}' byl smazán")
        else:
            raise Exception("Neznámý příkaz, který záhadným způsobem prošel validací")

    def loop(self):
        self._sort_commands()
        self._running = True
        try:
            # with patch_stdout():
            while True:
                if self._should_exit:
                    return
                inpt = self._prompt()
                if self._should_exit:
                    # If something requested exit but we are alredy asked user for input, exit here to prevent executing next command
                    return
                if inpt != "":
                    try:
                        self.proc_string(inpt)
                    except Exception as e:
                        if self.COMMAND_EXCEPTION_TRACEBACK:
                            c = console.Console()
                            t = traceback.Traceback(
                                show_locals=self.COMMAND_EXCEPTION_TRACEBACK_LOCALS
                            )
                            t.trace.stacks[0].frames = t.trace.stacks[0].frames[2:]
                            c.print(t)

                        if self.COMMAND_EXCEPTION_RERAISE:
                            raise e
        except KeyboardInterrupt as keyboard_interrupt:
            if self.END_ON_CTRL_C:
                self._should_exit = True
            if self.RAISE_ON_CTRL_C:
                raise keyboard_interrupt
        finally:
            self._running = False
            self._should_exit = False

    def _prompt(self) -> str:
        if self.RICH_PROMPT:
            rich_print(self.prompt, end="")
            return self._promt_session.prompt()
        else:
            return self._promt_session.prompt(self.prompt)

    def stop_loop(self):
        self._should_exit = True

    def parse_line(self, line: str, filter_empty: bool) -> list[list[str]]:
        output: list[list[str]] = [[]]
        for part in shlex.split(line):
            chunks = part.split(";")
            if len(chunks) == 1:
                output[-1].append(part)
            else:
                # chunk0;chunk1;chunk2;...;chunkX
                # ["chunk0", "chunk1", "chunk2", ..., "chunkX"]
                # "chunk0" patří k přechozímu příkazu,
                # "chunk1", "chunk2", ... jsou (celé) samostané příkazy,
                # "chunkX" je začátek následující příkazu, který může pokračovat v dalším partu
                output[-1].append(chunks[0])
                # `filter`, protože nechceme prázdný stringy pokud se bude parsovat tohle: ";;;;;;;;;"
                output += list(
                    filter(lambda x: x != "", map(lambda x: [x], chunks[1:-1]))
                )
                output.append([chunks[-1]])
        if filter_empty:
            output = list(filter(lambda x: len(x) != 0, output))
        return output

    def __python_exec(self, inpt: str):
        print(python_exec(inpt, self.PYTHON_EXEC_GLOBALS, self.PYTHON_EXEC_LOCALS))


def python_exec(
    string: str, globals_: dict[str, Any] | None, locals_: dict[str, Any] | None
) -> str:
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            exec(string, globals_, locals_)
        return out.getvalue()
    except:
        c = console.Console()
        t = traceback.Traceback()
        t.trace.stacks[0].frames = []  # IDK co jsem udělal, ale (asi) je to to co chci
        # Ok, asi to jsem tomu sebral funkcionalitu, ale alespoň jsou teď barvičky peepoHappy
        c.print(t)
    return ""
