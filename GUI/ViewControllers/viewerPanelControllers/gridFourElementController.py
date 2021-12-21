from GUI.Panels.viewerPanel.gridElement import GridElement
from GUI.ViewControllers.viewerPanelControllers.gridController import GridController
from GUI.ViewControllers.viewerPanelControllers.gridElementController import GridElementController
from GUI.Viewers.sliceViewer import SliceViewerVTK


class GridFourElementController(GridController):
    def __init__(self, gridView, viewerPanelController):
        GridController.__init__(self, viewerPanelController)

        self._view = gridView

        self._view0 = GridElement()
        self._view1 = GridElement()
        self._view2 = GridElement()
        self._view3 = GridElement()

        self.controller0 = GridElementController(self._view0, viewerPanelController)
        self.controller1 = GridElementController(self._view1, viewerPanelController)
        self.controller2 = GridElementController(self._view2, viewerPanelController)
        self.controller3 = GridElementController(self._view3, viewerPanelController)

        self.appendGridElementController(self.controller0)
        self.appendGridElementController(self.controller1)
        self.appendGridElementController(self.controller2)
        self.appendGridElementController(self.controller3)

        self._view.addBotLeftWidget(self._view0)
        self._view.addBotRightWidget(self._view1)
        self._view.addTopLeftWidget(self._view2)
        self._view.addTopRightWidget(self._view3)

        v = self.controller0.getDisplayView()
        if isinstance(v, SliceViewerVTK):
            v.setView('coronal')

        v = self.controller1.getDisplayView()
        if isinstance(v, SliceViewerVTK):
            v.setView('axial')

        v = self.controller2.getDisplayView()
        if isinstance(v, SliceViewerVTK):
            v.setView('sagittal')
