import logging
import os
import sys

from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore

from Core.api import API, FileLogger
from Core.Data.patientList import PatientList
from GUI.viewController import ViewController
import Script

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

    API.patientList = patientList
    API.logger.appendLoggingFunction(FileLogger().print)
    API.logger.enabled = True

    # instantiate the main GUI window
    viewController = ViewController(patientList)
    viewController.mainWindow.show()

    # Run start script
    scriptPath = os.path.join(str(Script.__path__[0]), 'startScript.py')
    try:
        with open(scriptPath, 'r') as file:
            code = file.read()

        output = API.interpreter._runCode(code)
        print(output)
    except Exception as err:
        print(format(err))

    app.exec_()
