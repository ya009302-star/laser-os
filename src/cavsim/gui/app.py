"""エントリポイント: `cavsim` コマンドまたは `python -m cavsim.gui.app`."""
import sys


def main():
    from PySide6 import QtWidgets
    from .main_window import MainWindow
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
