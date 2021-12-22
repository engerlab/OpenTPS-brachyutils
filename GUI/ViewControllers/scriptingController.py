import sys
from io import StringIO

from PyQt5.QtCore import QObject

from Controllers.api import API
from GUI.Panels.scriptingPanel.scriptingWindow import ScriptingWindow


class ScriptingController(QObject):
    def __init__(self, scriptingPanel):
        QObject.__init__(self)

        self._view = scriptingPanel

        self._view.newScriptingWindowSignal.connect(self.newScriptingWindow)

    def newScriptingWindow(self):
        self.scriptingWindow = ScriptingWindow(self)
        self.scriptingWindow.show()

    def run(self, code):
        api = API()

        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()
        try:
            exec(code)
        except Exception as err:
            sys.stdout = old_stdout
            return format(err)

        sys.stdout = old_stdout
        return redirected_output.getvalue()

