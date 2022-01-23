import threading

from Core.event import Event
from GUI.Viewer.DataForViewer.dataMultiton import DataMultiton
from GUI.Viewer.DataForViewer.image3DForViewer import Image3DForViewer


class ViewerDynSeq(DataMultiton):
    def __init__(self, seq):
        super().__init__(seq)

        if hasattr(self, '_images'):
            return

        self._image = None
        self._images = None
        self._ind = 0
        self._timer = None
        self.vtkOutputPortChangedSignal = Event(object)

        self._startTimer() # TODO: Start on demand!

    def _startTimer(self):
        self._images = self.data.dyn3DImageList
        self._timer = InfiniteTimer(0.5, self._setNextImage)
        self._timer.start()

    def _setNextImage(self):
        self._image = Image3DForViewer(self._images[self._ind])

        self._ind += 1

        if self._ind>= len(self._images):
            self._ind = 0

        self.vtkOutputPortChangedSignal.emit(self.vtkOutputPort)

    @property
    def vtkOutputPort(self):
        if self._image is None:
            return None
        return self._image.vtkOutputPort

class InfiniteTimer():
    """A Timer class that does not stop, unless you want it to."""

    def __init__(self, seconds, target):
        self._should_continue = False
        self.is_running = False
        self.seconds = seconds
        self.target = target
        self.thread = None

    def _handle_target(self):
        self.is_running = True
        self.target()
        self.is_running = False
        self._start_timer()

    def _start_timer(self):
        if self._should_continue: # Code could have been running when cancel was called.
            self.thread = threading.Timer(self.seconds, self._handle_target)
            self.thread.start()

    def start(self):
        if not self._should_continue and not self.is_running:
            self._should_continue = True
            self._start_timer()
        else:
            print("Timer already started or running, please wait if you're restarting.")

    def cancel(self):
        if self.thread is not None:
            self._should_continue = False # Just in case thread is running and cancel fails.
            self.thread.cancel()
        else:
            print("Timer never started or failed to initialize.")