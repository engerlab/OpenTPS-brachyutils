
from PyQt5.QtWidgets import QWidgetAction, QLabel

from opentps.gui.viewer.dataViewerComponents.dataViewerToolbar import DataViewerToolbar
from opentps.gui.viewer.dataViewerComponents.dvhPlot import DVHViewer


class DVHViewerActions:
    def __init__(self, dvhViewer:DVHViewer):
        self._dvhViewer = dvhViewer

        self._separator = None

        self._doseImageLabel = QLabel('')
        self._doseImageLabel.setFixedHeight(16)
        self._doseImageAction = QWidgetAction(None)
        self._doseImageAction.setDefaultWidget(self._doseImageLabel)

        self._handleDoseImage()

        self.hide()

        self._dvhViewer.doseChangeEvent.connect(self._handleDoseImage)

    def addToToolbar(self, toolbar:DataViewerToolbar):
        self._separator = toolbar.addSeparator()
        toolbar.addAction(self._doseImageAction)

    def hide(self):
        if not self._separator is None:
            self._separator.setVisible(False)
        self._doseImageAction.setVisible(False)

    def show(self):
        self._separator.setVisible(True)
        self._handleDoseImage()

    def _handleDoseImage(self, *args):
        if self._dvhViewer.dose is None:
            self._doseImageAction.setVisible(False)
        else:
            self._doseImageLabel.setText(self._dvhViewer.dose.name)
            #TODO:listen to name change event
            self._doseImageAction.setVisible(True)