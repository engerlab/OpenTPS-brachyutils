import logging

from PyQt5.QtWidgets import QApplication

from opentps.core.data import PatientList
from opentps.core.utils.programSettings import ProgramSettings
from opentps.gui.viewController import ViewController

logger = logging.getLogger(__name__)

patientList = PatientList()

def run():
    mainConfig = ProgramSettings()

    # options = parseArgs(sys.argv[1:])
    logger.info("Start Application")
    app = QApplication.instance()
    if not app:
        app = QApplication([])

    # instantiate the main opentps_core window
    viewController = ViewController(patientList)
    viewController.mainConfig = mainConfig
    viewController.mainWindow.show()

    app.exec_()


if __name__ == '__main__':
    run()