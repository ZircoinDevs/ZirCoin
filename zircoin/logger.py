from colorama import Fore, Style, init


class Logger():
    def __init__(self, name):
        self.name = name

    def info(self, text):
        print(Fore.CYAN + f"[{self.name.upper()}] " + Style.RESET_ALL + text)

    def error(self, text, fatal=False):
        print(Fore.RED + f"[{self.name.upper()}] " + Style.RESET_ALL + text)

        if fatal:
            input("Press enter to exit: ")
            exit()

    def urgent(self, text):
        print(Fore.RED + "[IMPORTANT] " + Style.RESET_ALL + text)
