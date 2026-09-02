import ttkbootstrap as ttkb

from map_quiz_maker.gui.main_window import MainWindow

# A ttkbootstrap 2.0 theme name. The old "flatly" still works but is a
# pre-2.0 alias that warns on use and is slated for removal in 3.0.
THEME = "sandstone-light"


def main():
    root = ttkb.Window(themename=THEME)
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
