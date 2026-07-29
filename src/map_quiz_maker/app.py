import ttkbootstrap as ttkb

from map_quiz_maker.gui.main_window import MainWindow


def main():
    root = ttkb.Window(themename="flatly")
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
