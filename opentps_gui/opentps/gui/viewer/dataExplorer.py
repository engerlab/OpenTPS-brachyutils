from PyQt5.QtWidgets import QMainWindow


# TODO A data explorer that shows all kind of data and allow basic operations (rename, save, etc.)
class DataExplorer(QMainWindow):
    def __init__(self, viewController, parent=None):
        super().__init__(parent)

        self._viewController = viewController
