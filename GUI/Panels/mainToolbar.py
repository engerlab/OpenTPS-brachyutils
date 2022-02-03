from PyQt5.QtWidgets import QToolBox

from GUI.Panels.patientDataPanel import PatientDataPanel
from GUI.Panels.roiPanel import ROIPanel
from GUI.Panels.scriptingPanel.scriptingPanel import ScriptingPanel
# from GUI.Panels.xRayProjectionPanel.xRayProjectionsPanel import XRayProjectionPanel


class MainToolbar(QToolBox):
    # For Damien:
    # Define mainImageSelectedSignal and connect it to patientDataPanelController.mainImageSelectedSignal (also to be defined)

    def __init__(self, viewController):
        QToolBox.__init__(self)

        self._viewController = viewController

        self.setStyleSheet("QToolBox::tab {font: bold; color: #000000; font-size: 16px;}")

        # initialize the 1st toolbox panel (patient data)
        self.patientDataPanel = PatientDataPanel(self._viewController)
        self.addItem(self.patientDataPanel, 'Patient data')

        # initialize the 2nd toolbox panel (ROI)
        roiPanel = ROIPanel(self._viewController)
        self.addItem(roiPanel, 'ROI')

        # TODO: When we get rid of patientDataPanelController we shoud have currentPatientChangedSignal in ViewController
        self._viewController.currentPatientChangedSignal.connect(roiPanel.setCurrentPatient)

        scriptingPanel = ScriptingPanel()
        self.addItem(scriptingPanel, 'Scripting')

        # xRayProjPanel = XRayProjectionPanel(self._viewController)
        # self.addItem(xRayProjPanel, 'Coucou')

