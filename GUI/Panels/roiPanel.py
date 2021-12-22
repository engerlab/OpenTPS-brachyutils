from PyQt5.QtWidgets import *
from PyQt5.QtGui import QColor, QPixmap, QIcon

from GUI.ViewControllers.ViewersControllers.roiContourViewerController import ROIContourViewerController


class ROIPanel(QWidget):
  def __init__(self):
    QWidget.__init__(self)
    self.items = []

    self.layout = QVBoxLayout()
    self.setLayout(self.layout)

  def addRTStruct(self, rtStructController):
    for contourController in rtStructController:
      checkbox = ROIItem(ROIContourViewerController(contourController)).getCheckbox()

      self.layout.addWidget(checkbox)
      self.items.append(checkbox)


  def removeRTStruct(self, contourController):
    for item in self.items:
      if item.getContourController() == contourController:
        self.layout.removeWidget(item)
        item.setParent(None)
        return


class ROIItem:
  def __init__(self, contourController):
    self._contourController = contourController

    name = contourController.getName()
    color = contourController.getColor()

    self.checkbox = QCheckBox(name)
    self.checkbox.setChecked(self._contourController.getVisible())

    self._contourController.visibleChangedSignal.connect(self.checkbox.setChecked)

    # When we click on the checkbox:
    stateChanged = lambda isChecked: self._contourController.setVisible(isChecked)
    self.checkbox.clicked.connect(stateChanged)

    pixmap = QPixmap(100, 100)
    pixmap.fill(QColor(color[0], color[1], color[2], 255))
    self.checkbox.setIcon(QIcon(pixmap))

  def getCheckbox(self):
    return self.checkbox

  def getContourController(self):
    return self._contourController
