from PyQt5.QtWidgets import QWidget


class Grid(QWidget):
    def __init__(self, viewController, parent):
        super().__init__(parent)

        self._gridElements = []
        self._viewController = viewController

    @property
    def gridElements(self):
        # Prevent from appending/removing to/from _gridElements
        return [element for element in self._gridElements]

    def appendGridElement(self, gridElement):
        self._gridElements.append(gridElement)

    def removeGridElement(self, gridElement):
        self._gridElements.remove(gridElement)
