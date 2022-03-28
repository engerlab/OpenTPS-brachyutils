import functools

from PyQt5.QtWidgets import QToolBox, QWidget

from Core.event import Event
from GUI.Panels.patientDataPanel import PatientDataPanel
from GUI.Panels.roiPanel import ROIPanel
from GUI.Panels.scriptingPanel.scriptingPanel import ScriptingPanel
from GUI.Panels.breathingSignalPanel import BreathingSignalPanel
from GUI.Panels.drrPanel import DRRPanel



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

        self.setStyleSheet("QToolBox::tab {font: bold; color: #000000; font-size: 16px;}")

        # initialize toolbox panels
        patientDataPanel = PatientDataPanel(self._viewController)
        roiPanel = ROIPanel(self._viewController)
        scriptingPanel = ScriptingPanel()
        breathingSignalPanel = BreathingSignalPanel(self._viewController)
        xRayProjPanel = DRRPanel(self._viewController)

        item = self.ToolbarItem(patientDataPanel, 'Patient data')
        self.showItem(item)
        item = self.ToolbarItem(roiPanel, 'ROI')
        self.showItem(item)
        item = self.ToolbarItem(scriptingPanel, 'Scripting')
        self.showItem(item)
        item = self.ToolbarItem(breathingSignalPanel, 'Breathing signal generation')
        self.showItem(item)
        item = self.ToolbarItem(xRayProjPanel, 'DRR')
        self.showItem(item)

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