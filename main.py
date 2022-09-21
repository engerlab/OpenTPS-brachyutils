import functools
import logging
import os
import sys
import threading
from pathlib import Path

from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore

from Core.api import API, FileLogger
from Core.Data._patientList import PatientList
from GUI.viewController import ViewController
import Script

from logConfigParser import parseArgs
from Core.Utils.programSettings import ProgramSettings
QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True) # avoid display bug for 4k resolutions with 200% GUI scale


logger = logging.getLogger(__name__)

def main():
    mainConfig = ProgramSettings()

    #options = parseArgs(sys.argv[1:])
    logger.info("Start Application")
    app = QApplication.instance()
    if not app:
        app = QApplication([])

    if API.patientList is None:
        patientList = PatientList()
        API.patientList = patientList

    API.logger.appendLoggingFunction(FileLogger().print)
    API.logger.appendLoggingFunction(logger.info)
    API.logger.enabled = True

    # instantiate the main GUI window
    patientList = API.patientList
    viewController = ViewController(patientList)
    viewController.mainConfig = mainConfig
    viewController.mainWindow.show()

    # Run start script
    scriptPath = os.path.join(mainConfig.startScriptFolder, 'startScript.py')
    if Path(scriptPath).is_file():
        with open(scriptPath, 'r') as file:
            code = file.read()

        # It would be nice to run this in a thread but since the application is not fully loaded yet we might get strange behavior
        output = API.interpreter.run(code)
        #runStartScript = functools.partial(API.interpreter.run, code)
        #threading.Thread(target=runStartScript).start()

        print('Start script output:')
        print(output)

    app.exec_()

if __name__ == '__main__':
    main()