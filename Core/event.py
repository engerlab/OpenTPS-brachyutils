
class Event:
    def __init__(self, *args):
        self._slots = []
        self.objectType = None

        if len(args) > 0:
            self.objectType = args[0]

    def connect(self, slot):
        self._slots.append(slot)

    def disconnect(self, slot):
        try:
            self._slots.remove(slot)
        except Exception as e:
            # TODO
            print(e)

    def emit(self, *args):
        if not(self.objectType is None):
            if len(args) != 1:
                raise ValueError('Incorrect argument')
            if not isinstance(args[0], self.objectType):
                raise ValueError('Incorrect argument')


        for slot in self._slots:
            try:
                slot(*args)
            except Exception as e:
                #TODO
                print(e)
