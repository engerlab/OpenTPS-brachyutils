from PyQt5.QtCore import QObject

from GUI.ViewControllers.SliceViewerController import SliceViewerController


class GridElementController(QObject):
    DVHDisplay = 'DVH'
    SliceViewerDisplay = 'SLICE'

    def __init__(self, parent=None):
        QObject.__init__(self)

        self._displayController = SliceViewerController()
        self._displayType = self.SliceViewerDisplay
        self._parent = parent

    def getDisplayController(self):
        return self._displayController

    def getDisplayType(self):
        return self._displayType

    def getSelectedImageController(self):
        return self._parent.getSelectedImageController()

    def notifyDroppedImage(self):
        if self._displayType==self.SliceViewerDisplay:
            self._displayController.setMainImage(self._parent.getSelectedImageController())

    def setDisplayType(self, displayType):
        self._displayType = displayType