from abc import abstractmethod


class AbstractImageViewer:
    @abstractmethod
    def primaryImage(self):
        pass

    @abstractmethod
    def secondaryImage(self):
        pass

    @abstractmethod
    def qActions(self):
        pass

    @abstractmethod
    def viewType(self):
        pass