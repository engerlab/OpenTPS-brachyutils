from PyQt5.QtWidgets import *
from PyQt5.QtGui import QColor, QPixmap, QIcon

from GUI.Viewer.ViewerData.viewerROIContour import ViewerROIContour


class ROIPanel(QWidget):
  def __init__(self, viewController):
    QWidget.__init__(self)

    self.items = []
    self.layout = QVBoxLayout()
    self._patient = None
    self._viewController = viewController

    self.setLayout(self.layout)

  def addRTStruct(self, rtStruct):
    for contour in rtStruct.contours:
      checkbox = ROIItem(ViewerROIContour(contour), self._viewController).getCheckbox()

      self.layout.addWidget(checkbox)
      self.items.append(checkbox)

  def removeRTStruct(self, contour):
    for item in self.items:
      if item.contour == contour:
        self.layout.removeWidget(item)
        item.setParent(None)
        return

  def setCurrentPatient(self, patient):
    if patient==self._patient:
      return

    self._patient = patient
    for rtStruct in self._patient.rtStructs:
      self.addRTStruct(rtStruct)

    self._patient.rtStructAddedSignal.connect(self.addRTStruct)
    self._patient.rtStructRemovedSignal.connect(self.removeRTStruct)


class ROIItem:
  def __init__(self, contour, viewController):
    self._contour = contour
    self._viewController = viewController

    self.checkbox = QCheckBox(contour.name)
    self.checkbox.setChecked(self._contour.visible)

    self._contour.visibleChangedSignal.connect(self.checkbox.setChecked)

    self.checkbox.clicked.connect(lambda c: self.handleClick(c))

    pixmap = QPixmap(100, 100)
    pixmap.fill(QColor(contour.color[0], contour.color[1], contour.color[2], 255))
    self.checkbox.setIcon(QIcon(pixmap))

  def getCheckbox(self):
    return self.checkbox

  @property
  def contour(self):
    return self._contour

  def handleClick(self, isChecked):
    self._contour.visible = isChecked
    self._viewController.showContour(self._contour)
