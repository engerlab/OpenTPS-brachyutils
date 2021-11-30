import pickle

from PyQt5.QtWidgets import QWidget, QVBoxLayout

from GUI.ViewControllers.SliceViewerController import SliceViewerController
from GUI.Viewers.sliceViewer import SliceViewerVTK


class GridElement(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._viewController = viewController

        self._displayController = None
        self.mainLayout = QVBoxLayout()

        self.setLayout(self.mainLayout)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        if self._viewController.getDisplayType()==self._viewController.SliceViewerDisplay:
            vtkWidget = SliceViewerVTK(self._viewController.getDisplayController())
            self.mainLayout.addWidget(vtkWidget)

            self.setAcceptDrops(True)

        #else: TODO

    def dragEnterEvent(self, e):
        e.accept()

    def dropEvent(self, e):
        if e.mimeData().hasText():
            if(e.mimeData().text()=='image'):
                self._viewController.notifyDroppedImage()
                e.accept()
                return
        e.ignore()


