from GUI.ViewControllers.viewerPanelControllers.gridController import GridController
from GUI.ViewControllers.viewerPanelControllers.gridElementController import GridElementController
from GUI.Viewers.sliceViewer import SliceViewerVTK


class GridFourElementController(GridController):
    def __init__(self, viewerPanelController):
        GridController.__init__(self, viewerPanelController)

        self.controller0 = GridElementController(viewerPanelController)
        self.controller1 = GridElementController(viewerPanelController)
        self.controller2 = GridElementController(viewerPanelController)
        self.controller3 = GridElementController(viewerPanelController)

        self.appendGridElementController(self.controller0)
        self.appendGridElementController(self.controller1)
        self.appendGridElementController(self.controller2)
        self.appendGridElementController(self.controller3)

        v = self.controller0.getDisplayView()
        if isinstance(v, SliceViewerVTK):
            v.setView('coronal')

        v = self.controller1.getDisplayView()
        if isinstance(v, SliceViewerVTK):
            v.setView('axial')

        v = self.controller2.getDisplayView()
        if isinstance(v, SliceViewerVTK):
            v.setView('sagittal')
