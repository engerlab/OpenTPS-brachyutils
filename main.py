
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore



QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True) # avoid display bug for 4k resolutions with 200% GUI scale

from GUI.MainWindow import *


if __name__ == '__main__':
  app = QApplication.instance()
  if not app:
    app = QApplication([])

  # instantiate the main GUI window
  #viewController = ViewController()
  mainWindow = MainWindow()
  mainWindow.show()

  app.exec_()
