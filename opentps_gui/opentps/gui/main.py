import logging

from PyQt5.QtWidgets import QApplication

from opentps.core.data import PatientList
from opentps.core.utils.programSettings import ProgramSettings
from opentps.gui.viewController import ViewController

logger = logging.getLogger(__name__)

patientList = PatientList()

mainConfig = ProgramSettings()

logger.info("Instantiate opentps gui")
app = QApplication.instance()
if not app:
    app = QApplication([])

# instantiate the main opentps_core window
viewController = ViewController(patientList)
viewController.mainConfig = mainConfig
mainWindow = viewController.mainWindow

def run():
    # options = parseArgs(sys.argv[1:])
    logger.info("Start opentps gui")

    mainWindow.show()
    app.exec_()

if __name__ == '__main__':
    run()