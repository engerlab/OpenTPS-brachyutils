
from opentps.gui import mainWindow, viewController
from opentps.gui.examples.extension.extension.gui.extensionPanel import ExtensionPanel


def addToGUI():
    mainWindow.mainToolbar.addWidget(ExtensionPanel(viewController), 'Extension example')