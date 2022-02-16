from PyQt5.QtWidgets import QToolBox

from GUI.Panels.patientDataPanel import PatientDataPanel
from GUI.Panels.roiPanel import ROIPanel
from GUI.Panels.scriptingPanel.scriptingPanel import ScriptingPanel
from GUI.Panels.drrPanel import DRRPanel


class MainToolbar(QToolBox):

    def __init__(self, viewController):
        QToolBox.__init__(self)

        self._viewController = viewController

        self.setStyleSheet("QToolBox::tab {font: bold; color: #000000; font-size: 16px;}")

        # initialize toolbox panels
        patientDataPanel = PatientDataPanel(self._viewController)
        roiPanel = ROIPanel(self._viewController)
        scriptingPanel = ScriptingPanel()

        self.addItem(patientDataPanel, 'Patient data')
        self.addItem(roiPanel, 'ROI')
        self.addItem(scriptingPanel, 'Scripting')

        xRayProjPanel = DRRPanel(self._viewController)
        self.addItem(xRayProjPanel, 'DRR')

