import threading

from Core.event import Event
from GUI.Viewer.DataForViewer.dataMultiton import DataMultiton


class ViewerDynSeq(DataMultiton):
    def __init__(self, seq):
        super().__init__(seq)

        self._timer = None
        self.timerSignal = Event(object)

    def startTimer(self):
        if not(self.timer is None) and self.timer.is_running:
            return
        self._timer = InfiniteTimer(0.04, self.onTimerEvent) #Refresh rate of 40 ms
        self._timer.start()

    def onTimerEvent(self):
        if len(self.timerSignal.slots) <= 0:
            self._timer.cancel()
        else:
            #Update what must be updated here
            pass

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