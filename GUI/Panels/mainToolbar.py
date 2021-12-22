from PyQt5.QtWidgets import QToolBox

from GUI.Panels.patientDataPanel import PatientDataPanel
from GUI.Panels.roiPanel import ROIPanel
from GUI.Panels.scriptingPanel.scriptingPanel import ScriptingPanel
from GUI.ViewControllers.patientDataPanelController import PatientDataPanelController
from GUI.ViewControllers.roiPanelController import ROIPanelController


class MainToolbar(QToolBox):
    # For Damien:
    # Define mainImageSelectedSignal and connect it to patientDataPanelController.mainImageSelectedSignal (also to be defined)

    def __init__(self, viewController):
        QToolBox.__init__(self)

        self._viewController = viewController

        self.setStyleSheet("QToolBox::tab {font: bold; color: #000000; font-size: 16px;}")

        # initialize the 1st toolbox panel (patient data)
        patientDataPanelController = PatientDataPanelController(self._viewController)
        patientDataPanel = PatientDataPanel(patientDataPanelController)
        self.addItem(patientDataPanel, 'Patient data')

        roiPanel = ROIPanel()
        self.roiPanelController = ROIPanelController(roiPanel)
        self.addItem(roiPanel, 'ROI')

        patientDataPanelController.currentPatientChangedSignal.connect(self.roiPanelController.setCurrentPatient)

        scriptingPanel = ScriptingPanel()
        self.addItem(scriptingPanel, 'Scripting')

