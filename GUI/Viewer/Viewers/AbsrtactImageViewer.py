from abc import abstractmethod


class AbstractImageViewer:
    @abstractmethod
    @property
    def primaryImage(self):
        pass

    @abstractmethod
    @property
    def secondaryImage(self):
        pass

    @abstractmethod
    @property
    def qActions(self):
        pass

    @abstractmethod
    @property
    def viewType(self):
        pass