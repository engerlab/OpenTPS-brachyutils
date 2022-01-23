import os
import sys
from io import StringIO

from Core.Data.Images.image3D import Image3D
from Core.Data.patient import Patient
import Script


class APIMethods:
    _methodNames = []

    def __setattr__(self, key, value):
        print('Adding method to api: '+str(key))
        if not (key in APIMethods._methodNames):
            APIMethods._methodNames.append(key)

        object.__setattr__(self, key, value)

    @staticmethod
    def getMethodsAsString():
        return APIMethods._methodNames


class _API:
    _apiMethods = APIMethods()
    _logging = True
    _dic = {"patientList": None}

    def __init__(self):
        # write log header
        if _API._logging:
            scriptPath = os.path.join(str(Script.__path__[0]), 'API_log.py')
            with open(scriptPath, 'a') as f:
                f.write('from Controllers.api import API\n')

    @property
    def patientList(self):
        return _API._dic["patientList"]

    @patientList.setter
    def patientList(self, patientList):
        _API._dic["patientList"] = patientList

    def __getattr__(self, item):
        return lambda *args, **kwargs: _API._wrappedMethod(_API._apiMethods.__getattribute__(item), *args, **kwargs)

    @staticmethod
    def _convertArgToString(arg):
        argStr = ''

        if isinstance(arg, Patient):
            argStr = 'API.patientList[' \
                     + str(_API._dic["patientList"].getIndex(arg)) + ']'
        elif isinstance(arg, Image3D):
            for patient in _API._dic["patientList"]:
                if patient.hasImage(arg):
                    argStr = 'API.patientList[' \
                             + str(_API._dic["patientList"].getIndex(patient)) + ']' \
                             + '.images[' \
                             + str(patient.getImageIndex(arg)) + ']'
        elif isinstance(arg, list):
            argStr = '['
            for elem in arg:
                argStr += _API._convertArgToString(elem) + ','

            argStr = argStr[:-1] + ']'
        elif isinstance(arg, tuple):
            argStr = '('
            for elem in arg:
                argStr += _API._convertArgToString(elem) + ','

            argStr = argStr[:-1] + ')'
        elif isinstance(arg, str):
            argStr = '\'' + arg + '\''
        else:
            argStr = str(arg)

        return argStr

    @staticmethod
    def enableLogging(enabled, fileName='default'):
        _API._logging = enabled

    @staticmethod
    def getMethodsAsString():
        return _API._apiMethods.getMethodsAsString()

    @staticmethod
    def _log(cmd):
        scriptPath = os.path.join(str(Script.__path__[0]), 'API_log.py')
        with open(scriptPath, 'a') as f:
            f.write(cmd + '\n')

    @staticmethod
    def registerToAPI(methodName, method):
        _API._apiMethods.__setattr__(methodName, method)

    @staticmethod
    def run(code):
        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()
        try:
            exec(code)
        except Exception as err:
            sys.stdout = old_stdout
            return format(err)

        sys.stdout = old_stdout
        return redirected_output.getvalue()

    @staticmethod
    def _wrappedMethod(method, *args, **kwargs):
        argsStr = ''

        if len(args) > 0:
            for arg in args:
                argStr = _API._convertArgToString(arg)
                argsStr += argStr + ','

        if len(kwargs)>0:
            for arg in kwargs.values():
                argStr = _API._convertArgToString(arg)
                argsStr += argStr + ','

        if len(args)>0 or len(kwargs)>0 or argsStr[-1] == ',':
            argsStr = argsStr[:-1]

        callStr = 'API.' + method.__name__ + '(' + argsStr + ')'

        if  _API._logging:
            _API._log(callStr)

        method(*args, **kwargs)

API = _API()
