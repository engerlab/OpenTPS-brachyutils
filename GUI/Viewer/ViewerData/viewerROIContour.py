
from Core.event import Event
from GUI.Viewer.ViewerData.viewerData import ViewerData


class ViewerROIContour(ViewerData):
    def __init__(self, roiContour):
        super().__init__(roiContour)
        if hasattr(self, '_wwlValue'):
            return

        self.visibleChangedSignal = Event(bool)

        self._visible = False

    def __setattr__(self, key, value):
        super().__setattr__(key, value)

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, visible):
        self._visible = visible
        self.visibleChangedSignal.emit(self._visible)
