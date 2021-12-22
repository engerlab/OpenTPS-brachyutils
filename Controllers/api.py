import sys
from io import StringIO

from Controllers.DataControllers.image3DController import Image3DController
from Controllers.DataControllers.patientController import PatientController
from Controllers.modelController import ModelController

class APIMethods:
    _methodNames = []
    _methods = []

    def __setattr__(self, key, value):
        self._methods.append(value)
        self._methodNames.append(key)
        object.__setattr__(self, key, value)

    def getMethodsAsString(self):
        return self._methodNames


class API(ModelController):
    _apiMethods = APIMethods()
    _logging = True

    def __init__(self, patientListController=None):
        ModelController.__init__(self, patientListController)

    def __getattr__(self, item):
        return lambda *args, **kwargs: self._wrappedMethod(self._apiMethods.__getattribute__(item), *args, **kwargs)

    def _convertArgToString(self, arg):
        argStr = ''

        if isinstance(arg, PatientController):
            argStr = 'api.patientListController[' \
                     + str(self.patientListController.getIndex(arg)) + ']'
        elif isinstance(arg, Image3DController):
            for patientController in self.patientListController:
                if patientController.hasImage(arg):
                    argStr = 'api.patientListController[' \
                             + str(self.patientListController.getIndex(patientController)) + ']' \
                             + '[' + str(patientController.getImageIndex(arg)) + ']'
        else:
            argStr = str(arg)

        return argStr

    def enableLogging(self, enabled, fileName='default'):
        self._logging = enabled

    def getMethodsAsString(self):
        return self._apiMethods.getMethodsAsString()

    def _log(self, str):
        #TODO
        print(str)

    def registerToAPI(methodName, method):
        API._apiMethods.__setattr__(methodName, method)

    @staticmethod
    def run(code):
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

    def _wrappedMethod(self, method, *args, **kwargs):
        argsStr = ''

        if len(args) > 0:
            for arg in args:
                argStr = self._convertArgToString(arg)
                argsStr += argStr + ','

        if len(kwargs)>0:
            for arg in kwargs.values():
                argStr = self._convertArgToString(arg)
                argsStr += argStr + ','

        if len(args)>0 or len(kwargs)>0 or argsStr[-1] == ',':
            argsStr = argsStr[:-1]

        callStr = method.__name__ + '(' + argsStr + ')'

        if self._logging:
            self._log(callStr)

        method(*args, **kwargs)
