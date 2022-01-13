import logging
import sys

from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore

from Controllers.instantiateAPI import instantiateAPI
from Core.Data.patientList import PatientList
from GUI.viewController import ViewController

from logConfigParser import parseArgs

QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True) # avoid display bug for 4k resolutions with 200% GUI scale


logger = logging.getLogger(__name__)

if __name__ == '__main__':

    options = parseArgs(sys.argv[1:])
    logger.info("Start Application")
    app = QApplication.instance()
    if not app:
        app = QApplication([])

    patientList = PatientList()

    #TODO Find a better way to instantiate the API
    instantiateAPI(patientList)

    # instantiate the main GUI window
    viewController = ViewController(patientList)
    viewController.mainWindow.show()

    app.exec_()
