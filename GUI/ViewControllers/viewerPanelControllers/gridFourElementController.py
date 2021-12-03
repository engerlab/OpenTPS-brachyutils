from GUI.ViewControllers.viewerPanelControllers.gridController import GridController
from GUI.ViewControllers.viewerPanelControllers.gridElementController import GridElementController


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
