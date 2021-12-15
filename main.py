
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore

from Controllers.DataControllers.patientListController import PatientListController
from Controllers.instantiateAPI import instantiateAPI
from Core.Data.patienList import PatientList
from GUI.ViewControllers.viewController import ViewController

QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True) # avoid display bug for 4k resolutions with 200% GUI scale

from GUI.MainWindow import *


if __name__ == '__main__':
    app = QApplication.instance()
    if not app:
        app = QApplication([])

    patientList = PatientList()
    patientListController = PatientListController(patientList)

    #TODO Find a better way to instantiate the API
    instantiateAPI(patientListController)

    # instantiate the main GUI window
    viewController = ViewController(patientListController)
    mainWindow = MainWindow(viewController)
    mainWindow.show()

    app.exec_()
