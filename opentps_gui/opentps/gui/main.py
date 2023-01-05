import logging
import unittest

from PyQt5.QtWidgets import QApplication

from opentps.core.data import PatientList
from opentps.core.utils.programSettings import ProgramSettings
from opentps.gui.viewController import ViewController


def viewController():
    # instantiate the main opentps_core window
    _viewController = ViewController(patientList)
    _viewController.mainConfig = mainConfig

    return _viewController

logger = logging.getLogger(__name__)

patientList = PatientList()

mainConfig = ProgramSettings()

logger.info("Instantiate opentps gui")
app = QApplication.instance()
if not app:
    app = QApplication([])

def runWithMainWindow(mainWindow):
    # options = parseArgs(sys.argv[1:])
    logger.info("Start opentps gui")

    mainWindow.show()
    app.exec_()

    mainWindow.close()
    #del mainWindow

def run():
    _viewController = viewController()
    runWithMainWindow(_viewController.mainWindow)

if __name__ == '__main__':
    run()

class MainTestCase(unittest.TestCase):
    def testRun(self):
        logger.info("Testing main window with view controller")
        _viewController = viewController()
        _viewController.mainWindow.show()
        _viewController.mainWindow.close()