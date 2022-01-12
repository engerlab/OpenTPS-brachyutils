
from Core.event import Event
from GUI.Viewer.ViewerData.viewerData import ViewerData


class ViewerROIContour(ViewerData):
    def __init__(self, roiContour):
        super().__init__(roiContour)

        self.visibleChangedSignal = Event(bool)

        if hasattr(self, '_wwlValue'):
            return

        self._visible = False

    def __setattr__(self, key, value):
        super().__setattr__(key, value)

    def __getattr__(self, item):
        if hasattr(self, item):
            return super().__getattribute__(item)
        else:
            return self.data.__getattribute__(item)

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, visible):
        self._visible = visible
        self.visibleChangedSignal.emit(self._visible)
