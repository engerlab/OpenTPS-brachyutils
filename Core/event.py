import copy


class Event:
    """
    A class that implements signal/slot mechanism similarly to pyQtSignal

    >>> signal = Event(bool)
    >>> signal.connect(lambda x: print(x))
    >>> signal.emit(True)
    True

    """

    def __init__(self, *args):
        self._slots = []
        self.objectType = None

        if len(args) > 0:
            self.objectType = args[0]

    def __getstate__(self):
        state = self.__dict__.copy()
        # Don't pickle methods in _slots
        state["_slots"] = []
        return state

    def __deepcopy__(self, memodict={}):
        newEvent = Event()

        newEvent.objectType = self.objectType

        for slot in self._slots:
            try:
                newSlot = copy.deepcopy(slot)
                newEvent.slots.append(newSlot)
            except:
                pass

        return newEvent

    def connect(self, slot):
        """
        Connects a slot
        """
        self._slots.append(slot)


    def disconnect(self, slot):
        """
        Disconnects a slot
        """
        if slot in self._slots:
            self._slots.remove(slot)


    def emit(self, *args):
        """
        Triggers execution of all connected slots with specified arguments
        """
        if not(self.objectType is None):
            if len(args) != 1:
                raise ValueError('Incorrect argument')
            if not isinstance(args[0], self.objectType):
                raise ValueError('Incorrect argument')

        for slot in self._slots:
            try:
                slot(*args)
            except Exception as e:
                raise(e)


    @property
    def slots(self):
        """
        List of slots (read-only)
        """
        return[slot for slot in self._slots]
