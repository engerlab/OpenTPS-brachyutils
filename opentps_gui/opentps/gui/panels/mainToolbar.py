import functools
import glob
import logging
import os

from PyQt5.QtWidgets import QToolBox, QWidget

from opentps.core import Event
from opentps.gui.panels.doseComparisonPanel import DoseComparisonPanel
from opentps.gui.panels.doseComputationPanel import DoseComputationPanel
from opentps.gui.panels.patientDataPanel.patientDataPanel import PatientDataPanel
from opentps.gui.panels.planDesignPanel.planDesignPanel import PlanDesignPanel
from opentps.gui.panels.planEvaluationPanel import PlanEvaluationPanel
from opentps.gui.panels.planOptimizationPanel.planOptiPanel import PlanOptiPanel
from opentps.gui.panels.roiPanel import ROIPanel
from opentps.gui.panels.scriptingPanel.scriptingPanel import ScriptingPanel
from opentps.gui.panels.registrationPanel import RegistrationPanel

logger = logging.getLogger(__name__)


class MainToolbar(QToolBox):
    class ToolbarItem:
        def __init__(self, panel:QWidget, panelName:str):
            self.visibleEvent = Event(bool)

            self.panel = panel
            self.panelName = panelName
            self.itemNumber = None

            self._visible = True

        @property
        def visible(self) -> bool:
            return self._visible

        @visible.setter
        def visible(self, visible:bool):
            if visible==self._visible:
                return

            self._visible = visible
            self.visibleEvent.emit(self._visible)

    def __init__(self, viewController):
        QToolBox.__init__(self)

        self._viewController = viewController
        self._items = []
        self._maxWidth = 270

        self.setStyleSheet("QToolBox::tab {font: bold; color: #000000; font-size: 16px;}")

        # initialize toolbox panels
        patientDataPanel = PatientDataPanel(self._viewController)
        roiPanel = ROIPanel(self._viewController)
        planDesignPanel = PlanDesignPanel(self._viewController)
        planDesignPanel.setMaximumWidth(self._maxWidth)
        planOptiPanel = PlanOptiPanel(self._viewController)
        planOptiPanel.setMaximumWidth(self._maxWidth)
        dosePanel = DoseComputationPanel(self._viewController)
        dosePanel.setMaximumWidth(self._maxWidth)
        planEvaluationPanel = PlanEvaluationPanel(self._viewController)
        planEvaluationPanel.setEnabled(False)
        doseComparisonPanel = DoseComparisonPanel(self._viewController)
        scriptingPanel = ScriptingPanel()
        #breathingSignalPanel = BreathingSignalPanel(self._viewController)
        #xRayProjPanel = DRRPanel(self._viewController)
        registrationPanel = RegistrationPanel(self._viewController)

        self.addWidget(patientDataPanel, 'Patient data')
        self.addWidget(roiPanel, 'ROI')
        self.addWidget(planDesignPanel, 'Plan design')
        self.addWidget(planOptiPanel, 'Plan optimization')
        self.addWidget(dosePanel, 'Dose computation')
        self.addWidget(planEvaluationPanel, "Plan evaluation")
        self.addWidget(doseComparisonPanel, 'Dose comparison')
        self.addWidget(scriptingPanel, 'Scripting')

    def addWidget(self, widget:QWidget, name:str):
        item = self.ToolbarItem(widget, name)
        self.showItem(item)
        item.visibleEvent.connect(functools.partial(self._handleVisibleEvent, item))

    def _handleVisibleEvent(self, item:ToolbarItem, visible:bool):
        if visible:
            self.showItem(item)
        else:
            self.hideItem(item)

    def showItem(self, item):
        if item in self._items:
            return

        self._items.append(item)
        self.addItem(item.panel, item.panelName)

    def hideItem(self, item):
        if not(item in self._items):
            return

        self.removeItem(self._items.index(item))
        self._items.remove(item)

    @property
    def items(self):
        return [item for item in self._items]
