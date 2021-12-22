from PyQt5.QtWidgets import QWidget


class Grid(QWidget):
    def __init__(self, viewController):
        QWidget.__init__(self)

        self._gridElements = []
        self._viewController = viewController

    def appendGridElement(self, gridElement):
        self._gridElements.append(gridElement)

    def getGridElelements(self):
        return self._gridElements

    def removeGridElement(self, gridElement):
        self._gridElements.remove(gridElement)
