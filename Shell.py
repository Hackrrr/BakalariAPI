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
    def __init__(self, name: str, callback, argparser: argparse.ArgumentParser = None, shortHelp: str = "", aliases: list[str] = [], spreadArguments = False):
        self.Name: str = name
        self.Argparser: argparse.ArgumentParser = argparser
        if self.Argparser != None:
            self.Argparser.prog = name
        self.Callback = callback #Passing dict with values from Argparser
        self.ShortHelp: str = shortHelp
        self.Aliases: list[str] = aliases
        self.SPREAD_ARGUMENTS = spreadArguments

    # def Invoke(self, argumentList: list):
    #     self(*argumentList)
    def __call__(self, *args):
        if self.Argparser == None:
            self.Callback()
        else:
            try:
                try:
                    parsed = self.Argparser.parse_args(args)
                except SystemExit: # Because when -h or --help is present, Argument parser (tries to) exit program
                    return
            except ValueError: # Because when parser fails it raise ValueError (and if not catched)
                pass
            else:
                if self.SPREAD_ARGUMENTS:
                    self.Callback(**parsed.__dict__)
                else:
                    self.Callback(parsed)

class Shell:
    Regex: re.Pattern = re.compile(r"(?<=\s)(?:((?:(?<!\\)\".+?(?<!\\)\")|(?:(?<!\\)'.+?(?<!\\)'))|((?:.(?<!\s))+?))(?=\s|$)")

    def __init__(
            self,
            prompt: str = "> ",
            commands: list[Command] = [],
            generateCommands: list[str] = ["help", "prompt", "exit"],
            firstCommandCaseSensitive: bool = False,
            allowShorhands: bool = True,
            allowPythonExec: bool = False,
            pythonExecPrefix: str = None,
            exitOnCtrlC: bool = True,
            raiseOnCtrlC: bool = False
            ):
        self.Prompt: str = prompt
        self.Commands: dict[str, Command] = {}

        self.FIRST_COMMAND_CASE_SENSITIVE: bool = firstCommandCaseSensitive
        self.ALLOW_SHORTHANDS: bool = allowShorhands
        self.ALLOW_PYTHON_EXEC: bool = allowPythonExec
        self.PYTHON_EXEC_PREFIX: str = pythonExecPrefix
        self.EXIT_ON_CTRL_C: bool = exitOnCtrlC
        self.RAISE_ON_CTRL_C: bool = raiseOnCtrlC

        self.shouldExit: bool = False

        for command in commands:
            self.AddCommand(command)

        if generateCommands == None:
            generateCommands = []
        
        for command in generateCommands:
            if command == "help" or command == "?":
                self.AddCommand(Command(
                    "help",
                    self.PrintHelp,
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
                self.AddCommand(
                    Command(
                        "prompt",
                        self.ChangePrompt,
                        parser,
                        "Změní prompt text",
                        spreadArguments=True
                    )
                )
            elif command == "exit":
                self.AddCommand(Command(
                    "exit",
                    self.ExitLoop,
                    None,
                    "Ukončí shell"
                ))
            # else:
            #     raise Exception("Unknown command to generate")
    
    def AddCommand(self, command: Command):
        self.Commands[command.Name if self.FIRST_COMMAND_CASE_SENSITIVE else command.Name.lower()] = command
        # for alias in command.Aliases:
        #     self.Commands[alias if self.FIRST_COMMAND_CASE_SENSITIVE else alias.lower()] = command

    def ProcString(self, string: str):
        if self.ALLOW_PYTHON_EXEC and self.PYTHON_EXEC_PREFIX != None and string.startswith(self.PYTHON_EXEC_PREFIX):
            PythonExec(string[len(self.PYTHON_EXEC_PREFIX):])
            return
        parsed = self.ParseLine(string)
        if len(parsed) == 0:
            return
        first = parsed.pop(0)
        if not self.FIRST_COMMAND_CASE_SENSITIVE:
            first = first.lower()
        if not self.ALLOW_SHORTHANDS:
            if first in self.Commands:
                self.Commands[first](*parsed)
            else:
                if self.ALLOW_PYTHON_EXEC and self.PYTHON_EXEC_PREFIX == None:
                    PythonExec(string)
                else:
                    print(f"Neznámý příkaz '{string}'\nZkus napsat 'help' nebo '?' pro nápovědu")
        else:
            fullMatch = None
            candidates = [] #TODO: Pokud má příkaz alias, tak může kovliktovat sám se sebou
            for _, command in self.Commands.items():
                for commandName in [command.Name] + command.Aliases:
                    if commandName.startswith(first):
                        if len(first) == len(commandName):
                            fullMatch = command
                            break
                        candidates.append(command)
            if fullMatch != None:
                fullMatch(*parsed)
            else:
                candidatesCount = len(candidates)
                if candidatesCount == 0:
                    if self.ALLOW_PYTHON_EXEC and self.PYTHON_EXEC_PREFIX == None:
                        PythonExec(string)
                    else:
                        print(f"Neznámý příkaz '{string}'\nZkus napsat 'help' nebo '?' pro nápovědu")
                elif candidatesCount == 1:
                    candidates[0](*parsed)
                else:
                    print("Nejednoznačný příkaz; Možní kándidáti:")
                    for candidate in candidates:
                        print("%-20s %s" % (candidate.Name, candidate.ShortHelp))
            
    def PrintHelp(self):
        print("Možné příkazy:")
        for _, command in self.Commands.items():
            print("\t%-25s - %s" % (" | ".join([command.Name] + command.Aliases), command.ShortHelp))
    
    def ChangePrompt(self, text: str):
        self.Prompt = text

    def StartLoop(self):
        try:
            while True:
                if self.shouldExit: # If something requested exit, exit
                    return
                inpt = input(self.Prompt)
                if self.shouldExit: # If something requested exit but we are alredy asked user for input, exit here to prevent executing next command
                    return
                if inpt != "":
                    self.ProcString(inpt)
        except KeyboardInterrupt:
            if self.RAISE_ON_CTRL_C:
                raise KeyboardInterrupt
            if self.EXIT_ON_CTRL_C:
                self.shouldExit = True
    
    def ExitLoop(self): # TODO: Try find a way how to "terminate" input function (or do custom input system (by recording keys and have buffer for it))
        self.shouldExit = True

    def ParseLine(self, line: str) -> list[str]:
        parsed = []
        regexSplit = self.Regex.findall(" " + line) #Mezera před stringem, protože python regex engine nepodporuje začátek stringu v look-behind (resp. variabilní délku look-behind(u))
        for part in regexSplit:
            parsed.append(part[1] if part[0] == "" else part[0][1:-1])
        return parsed

def PythonExec(string: str):
    # #Idea taken from here: https://stackoverflow.com/questions/3906232/python-get-the-print-output-in-an-exec-statement
    # print(f"Executing: {string}")
    # original_stdout = sys.stdout
    # buffer = sys.stdout = StringIO()
    # try:
    #     exec(string)
    # finally:
    #     sys.stdout = original_stdout
    #     print(buffer.getvalue())
    # print(f"Executed: {string}")
    # print(f"Buffer: {buffer}")

    #TODO: Better PythonExec() (filter None value / better way than this print hack)
    try:
        exec(f"print({string})")
    except Exception as e:
        print(e)
