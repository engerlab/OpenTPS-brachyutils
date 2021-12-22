import sys
from io import StringIO

from PyQt5.QtCore import QObject

from Controllers.api import API
from GUI.Panels.scriptingPanel.scriptingWindow import ScriptingWindow


class ROIPanelController(QObject):
    def __init__(self, roiPanel):
        QObject.__init__(self)

        self._patientController = None
        self._view = roiPanel

    def setCurrentPatient(self, patientController):
        self._patientController = patientController
        self._view.addRTStruct(self._patientController.getRTStructControllers())

        self._patientController.rtStructAddedSignal.connect(self._view.addRTStruct)
        self._patientController.rtStructRemovedSignal.connect(self._view.removeRTStruct)

        #TODO: disconnect
