from GUI.ViewControllers.viewerPanelControllers.gridController import GridController
from GUI.ViewControllers.viewerPanelControllers.gridElementController import GridElementController


class GridFourElementController(GridController):
    def __init__(self, viewController):
        GridController.__init__(self, viewController)

        self.controller0 = GridElementController(parent=self)
        self.controller1 = GridElementController(parent=self)
        self.controller2 = GridElementController(parent=self)
        self.controller3 = GridElementController(parent=self)

        self.appendGridElementController(self.controller0)
        self.appendGridElementController(self.controller1)
        self.appendGridElementController(self.controller2)
        self.appendGridElementController(self.controller3)
