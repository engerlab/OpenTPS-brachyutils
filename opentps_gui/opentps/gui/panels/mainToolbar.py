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
from opentps.gui.panels.planOptimizationPanel.planOptiPanel import PlanOptiPanel
from opentps.gui.panels.roiPanel import ROIPanel
from opentps.gui.panels.scriptingPanel.scriptingPanel import ScriptingPanel
from opentps.gui.panels.registrationPanel import RegistrationPanel

import opentps.gui.extensions as extensionModule


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
        doseComparisonPanel = DoseComparisonPanel(self._viewController)
        scriptingPanel = ScriptingPanel()
        #breathingSignalPanel = BreathingSignalPanel(self._viewController)
        #xRayProjPanel = DRRPanel(self._viewController)
        registrationPanel = RegistrationPanel(self._viewController)

        item = self.ToolbarItem(patientDataPanel, 'Patient data')
        self.showItem(item)
        item = self.ToolbarItem(roiPanel, 'ROI')
        self.showItem(item)
        item = self.ToolbarItem(planDesignPanel, 'plan design')
        self.showItem(item)
        item = self.ToolbarItem(planOptiPanel, 'plan optimization')
        self.showItem(item)
        item = self.ToolbarItem(dosePanel, 'Dose computation')
        self.showItem(item)
        item = self.ToolbarItem(doseComparisonPanel, 'Dose comparison')
        self.showItem(item)
        item = self.ToolbarItem(scriptingPanel, 'Scripting')
        self.showItem(item)
        #item = self.ToolbarItem(breathingSignalPanel, 'Breathing signal generation')
        #self.showItem(item)
        #item = self.ToolbarItem(xRayProjPanel, 'DRR')
        #self.showItem(item)
        item = self.ToolbarItem(registrationPanel, 'registration')
        self.showItem(item)

        self._addExtenstions()

        self._addVisibilityListenerToAllItems()

    def _addVisibilityListenerToAllItems(self):
        for item in self._items:
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

    def _addExtenstions(self):
        extensionFilesFromDir = lambda d:[f for f in glob.glob(os.path.join(d, "*.py")) if "extension" in f or "Extension"]
        extensionFiles = extensionFilesFromDir(extensionModule.__path__[0])
        subdirs = glob.glob(os.path.join(extensionModule.__path__[0], '*/'), recursive=False)
        for subdir in subdirs:
            extensionFiles.extend(extensionFilesFromDir(subdir))

        for extensionFile in extensionFiles:
            try:
                extensionName = os.path.splitext(os.path.basename(extensionFile))[0]

                strToEval = 'from extensions.'
                extensionsFound = False
                for dirElem in extensionFile.split(os.path.sep):
                    if extensionsFound:
                        if os.path.splitext(dirElem)[0]==extensionName:
                            break
                        else:
                            strToEval += dirElem + '.'
                    else:
                        if dirElem=='extensions':
                            extensionsFound = True


                strToEval +=  extensionName + ' import Panel\n'
                strToEval += 'p = Panel(self._viewController)\n'
                strToEval += 'item = self.ToolbarItem(p, \'' + extensionName + '\')\n'
                strToEval += 'self.showItem(item)'
                exec(strToEval)
            except Exception as e:
                logger.error(str(e))

