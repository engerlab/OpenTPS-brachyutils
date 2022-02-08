import functools
import inspect
import logging
import os
import sys
import unittest
from io import StringIO
from typing import Callable

import Script


class FileLogger():
    """
    A simple logger that appends inputs to a file
    """
    def __init__(self):
        self.scriptPath = os.path.join(str(Script.__path__[0]), 'API_log.py')

    def print(self, cmd: str):
        """
        Append cmd to file
        Args:
            cmd (str):  The command to log
        """
        with open(self.scriptPath, 'a') as f:
            f.write(cmd + '\n')


class APILogger:
    """
       Log code in a string format which can be executed by APIInterpreter.
       """
    _staticVars = {"enabled": False, "logLock": False, "logKey": None}
    _loggerFunctions = []

    class LogKey:
        pass

    @staticmethod
    def appendLoggingFunction(func: Callable[[str], None]):
        """
            Add a new logging function.
            Args:
                cmd (Callable[[str], None]):  Function that will be called each time a str must be logged
        """
        if func not in APILogger._loggerFunctions:
            APILogger._loggerFunctions.append(func)

    @staticmethod
    def removeLoggingFunction(func: Callable[[str], None]):
        """
            Remove a logging function
            Args:
                cmd (Callable[[str], None]):  Function previously added to APILogger by appendLoggingFunction
        """
        APILogger._loggerFunctions.append(func)

    @staticmethod
    def loggedViaAPI(method):
        """
        Decorator for functions and methods that we want to be logged.
        """
        methodIsStatic = True
        try:
            cls = get_class_that_defined_method(method)
            if not cls is None:
                methodIsStatic = isinstance(inspect.getattr_static(cls, method.__name__), staticmethod)
        except:
            pass

        if not methodIsStatic:
            raise ValueError('method cannot be a non static class method')

        return lambda *args, **kwargs: APILogger._wrappedMethod(method, *args, **kwargs)

    @property
    def enabled(self) -> bool:
        """
        APILogger is enabled
        :type: bool
        """
        return APILogger._staticVars["enabled"]

    @enabled.setter
    def enabled(self, e: bool):
        APILogger._staticVars["enabled"] = e

    @staticmethod
    def _wrappedMethod(method, *args, **kwargs):
        loggerEnabled = APILogger._staticVars["enabled"]
        loggerAlreadyLogging = APILogger._staticVars["logLock"]

        if not loggerEnabled:
            return lambda *args, **kwargs: method(*args, **kwargs)

        newLogKey = APILogger.LogKey()

        # If we are already logging but enter _wrappedMethod this means that the present method is a method called by the method already logging.
        # We only log the top level method
        if not loggerAlreadyLogging:
            callStr = APILogger._loggedMethodToString(method, *args, **kwargs)
            APILogger._log(callStr)
            APILogger._lockLogger(newLogKey)

        # In any case we must execute the method
        try:
            method(*args, **kwargs)
        except Exception as e:
            APILogger._tryUnlockLogger(newLogKey)
            raise (e)

        APILogger._tryUnlockLogger(newLogKey)

    @staticmethod
    def _lockLogger(key):
        if APILogger._staticVars["logLock"]:
            raise Exception('Logger already locked!')

        APILogger._staticVars["logKey"] = key
        APILogger._staticVars["logLock"] = True

    @staticmethod
    def _tryUnlockLogger(key):
        if key == APILogger._staticVars["logKey"]:
            APILogger._staticVars["logKey"] = None
            APILogger._staticVars["logLock"] = False


    @staticmethod
    def _log(cmd):
        for logFunction in APILogger._loggerFunctions:
            logFunction(cmd)

        logging.info(cmd)

    @staticmethod
    def _loggedMethodToString(method, *args, **kwargs):
        callStr = method.__name__ + '(' + APILogger._LoggedArgsToString(*args, **kwargs) + ')'

        isFunction = True
        isstatic = True
        try:
            cls = get_class_that_defined_method(method)
            if not cls is None:
                # isstatic = isinstance(inspect.getattr_static(cls, method.__name__), staticmethod)
                isFunction = False
        except:
            pass
        if isstatic and not isFunction:
            callStr = cls.__name__ + '.' + callStr

        return callStr

    @staticmethod
    def _LoggedArgsToString(*args, **kwargs):
        argsStr = ''

        if len(args) > 0:
            for arg in args:
                argsStr += APILogger._LoggedArgToString(arg) + ','

        if len(kwargs) > 0:
            for arg in kwargs.values():
                #TODO: Add kwargName= to string!
                argsStr += APILogger._LoggedArgToString(arg) + ','

        if len(args) > 0 or len(kwargs) > 0 or argsStr[-1] == ',':
            argsStr = argsStr[:-1]

        return argsStr

    @staticmethod
    def _LoggedArgToString(arg):
        # Do import here to avoid circular import at compilation time
        from Core.Data.Images.image3D import Image3D
        from Core.Data.patient import Patient
        from Core.Data.patientList import PatientList

        argStr = ''

        if isinstance(arg, PatientList):
            argStr = 'API.patientList'
        elif isinstance(arg, Patient):
            argStr = APILogger._patientToString(arg)
        elif isinstance(arg, Image3D):
            argStr = APILogger._image3DToString(arg)
        elif isinstance(arg, list):
            argStr = APILogger._listToString(arg)
        elif isinstance(arg, tuple):
            argStr = APILogger._tupleToString(arg)
        elif isinstance(arg, str):
            argStr = '\'' + arg + '\''
        else:
            argStr = str(arg)

        return argStr

    @staticmethod
    def _patientToString(patient):
        argStr = ''

        ind = _API._staticVars["patientList"].getIndex(patient)
        if ind < 0:
            argStr = 'Error: Image or patient not found in patient'
        else:
            argStr = 'API.patientList[' \
                     + str(ind) + ']'

        return argStr

    @staticmethod
    def _image3DToString(image):
        argStr = ''

        for patient in _API._staticVars["patientList"]:
            if patient.hasImage(image):
                argStr = 'API.patientList[' \
                         + str(_API._staticVars["patientList"].getIndex(patient)) + ']' \
                         + '.images[' \
                         + str(patient.getImageIndex(image)) + ']'
        if argStr == '':
            argStr = 'Error: Image or patient not found in patient or patient list'

        return argStr

    @staticmethod
    def _listToString(l: list):
        argStr = '['
        for elem in l:
            argStr += APILogger._LoggedArgToString(elem) + ','

        argStr = argStr[:-1] + ']'

        return argStr

    @staticmethod
    def _tupleToString(t: tuple):
        argStr = '('
        for elem in t:
            argStr += APILogger._LoggedArgToString(elem) + ','

        argStr = argStr[:-1] + ')'

        return argStr

class APIInterpreter:
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

class _API:
    _staticVars = {"patientList": None}
    _logger = APILogger()
    _interpreter = APIInterpreter()

    @property
    def logger(self):
        return self._logger

    @property
    def interpreter(self):
        return self._interpreter

    @property
    def patientList(self):
        return _API._staticVars["patientList"]

    @patientList.setter
    def patientList(self, patientList):
        _API._staticVars["patientList"] = patientList

    @staticmethod
    def loggedViaAPI(method):
        return APILogger.loggedViaAPI(method)

API = _API()

def get_class_that_defined_method(meth):
    if isinstance(meth, functools.partial):
        return get_class_that_defined_method(meth.func)
    if inspect.ismethod(meth) or (inspect.isbuiltin(meth) and getattr(meth, '__self__', None) is not None and getattr(meth.__self__, '__class__', None)):
        for cls in inspect.getmro(meth.__self__.__class__):
            if meth.__name__ in cls.__dict__:
                return cls
        meth = getattr(meth, '__func__', meth)  # fallback to __qualname__ parsing
    if inspect.isfunction(meth):
        cls = getattr(inspect.getmodule(meth),
                      meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0],
                      None)
        if isinstance(cls, type):
            return cls
    return getattr(meth, '__objclass__', None)  # handle special descriptor objects


class EventTestCase(unittest.TestCase):
    @API.loggedViaAPI
    def loggedMethod(self):
        return True

    def testDisabled(self):
        self.assertFalse(API.logger.enabled)
        self.assertTrue(self.loggedMethod())
