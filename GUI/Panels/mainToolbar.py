import functools
import glob
import logging
import os

from PyQt5.QtWidgets import QToolBox, QWidget

from Core.event import Event
from GUI.Panels.doseComparisonPanel import DoseComparisonPanel
from GUI.Panels.doseComputationPanel import DoseComputationPanel
from GUI.Panels.PatientDataPanel.patientDataPanel import PatientDataPanel
from GUI.Panels.PlanDesignPanel.planDesignPanel import PlanDesignPanel
from GUI.Panels.PlanOptimizationPanel.planOptiPanel import PlanOptiPanel
from GUI.Panels.roiPanel import ROIPanel
from GUI.Panels.ScriptingPanel.scriptingPanel import ScriptingPanel
from GUI.Panels.breathingSignalPanel import BreathingSignalPanel
from GUI.Panels.drrPanel import DRRPanel

import Extensions as extensionModule


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
        doseComparisonPanel = DoseComparisonPanel(self._viewController)
        scriptingPanel = ScriptingPanel()
        breathingSignalPanel = BreathingSignalPanel(self._viewController)
        xRayProjPanel = DRRPanel(self._viewController)

        item = self.ToolbarItem(patientDataPanel, 'Patient data')
        self.showItem(item)
        item = self.ToolbarItem(roiPanel, 'ROI')
        self.showItem(item)
        item = self.ToolbarItem(planDesignPanel, 'Plan design')
        self.showItem(item)
        item = self.ToolbarItem(planOptiPanel, 'Plan optimization')
        self.showItem(item)
        item = self.ToolbarItem(dosePanel, 'Dose computation')
        self.showItem(item)
        item = self.ToolbarItem(doseComparisonPanel, 'Dose comparison')
        self.showItem(item)
        item = self.ToolbarItem(scriptingPanel, 'Scripting')
        self.showItem(item)
        item = self.ToolbarItem(breathingSignalPanel, 'Breathing signal generation')
        self.showItem(item)
        item = self.ToolbarItem(xRayProjPanel, 'DRR')
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

                strToEval = 'from Extensions.'
                extensionsFound = False
                for dirElem in extensionFile.split(os.path.sep):
                    if extensionsFound:
                        if os.path.splitext(dirElem)[0]==extensionName:
                            break
                        else:
                            strToEval += dirElem + '.'
                    else:
                        if dirElem=='Extensions':
                            extensionsFound = True


                strToEval +=  extensionName + ' import Panel\n'
                strToEval += 'p = Panel(self._viewController)\n'
                strToEval += 'item = self.ToolbarItem(p, \'' + extensionName + '\')\n'
                strToEval += 'self.showItem(item)'
                exec(strToEval)
            except Exception as e:
                logger.error(str(e))

