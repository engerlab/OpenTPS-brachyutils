
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore

QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True) # avoid display bug for 4k resolutions with 200% GUI scale

from GUI.MainWindow import *


app = QApplication.instance() 
if not app: 
  app = QApplication([])

#app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

# instantiate the main GUI window
main_window = MainWindow()
main_window.show()

app.exec_()
