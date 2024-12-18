import curses


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
        self.input_window.nodelay(True)
        self.stdscr.nodelay(True)
#        curses.noecho()
#        curses.cbreak()
#        self.stdscr.keypad(True)
#        self.input_window.keypad(True)

    def update_input_window(self, msg):
        self.input_window.clear()
        self.input_window.addstr("> " + msg)
        self.input_window.refresh()

    def exit(self):
        print("Exiting Gui...")
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()

