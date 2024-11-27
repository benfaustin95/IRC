import curses

class Mgr:
    def __init__(self) -> None:
        self.gui = None
        curses.wrapper(self.run_gui)

    def run_gui(self, stdscr):
        self.gui = Gui(stdscr)
        while True:
            self.gui.output_window.refresh()
            self.gui.input_window.refresh()
            self.gui.input_window.move(0, 2)
            self.gui.input_window.clrtoeol()
            curses.echo()
            user_input = self.gui.input_window.getstr().decode("utf-8")
            curses.noecho()
            if user_input.strip().lower() == "exit":
                break

            self.gui.output_window.addstr(f">> {user_input}")
            self.gui.output_window.refresh()

        self.gui.exit()



class Gui:
    def __init__(self, stdscr) -> None:
        self.output_window = None
        self.input_window = None
        self.stdscr = stdscr
        self.input_height = 0
        self.output_height = 0
        self.height = 0
        self.width = 0
        self.build_windows() 

    def build_windows(self):
        self.stdscr.clear()
        curses.curs_set(0)
        self.height,self.width = self.stdscr.getmaxyx()
        self.input_height = 3
        self.output_height = self.height - self.input_height
        self.output_window = curses.newwin(self.output_height, self.width, 0, 0)
        self.output_window.scrollok(True)

        self.input_window = curses.newwin(self.input_height, self.width, self.output_height, 0)
        self.input_window.addstr(0,0,"> ")
#        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        self.input_window.keypad(True)



    def exit(self):
        print("Exiting Gui...")
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()


if __name__ == "__main__":
    mgr = Mgr()