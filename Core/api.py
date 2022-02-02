import functools
import inspect
import os
import sys
import types
from io import StringIO

from Core.Data.Images.image3D import Image3D
from Core.Data.patient import Patient
import Script
from Core.Data.patientList import PatientList


class _API:
    _logging = True
    _dic = {"patientList": None}
    _apiClasses = []
    _logLock = False
    _logKey = None

    def __init__(self):
        pass


    @staticmethod
    def apiMethod(method):
        isstatic = True
        try:
            cls = get_class_that_defined_method(method)
            if not cls is None:
                isstatic = isinstance(inspect.getattr_static(cls, method.__name__), staticmethod)
        except:
            pass
        if not isstatic:
            raise ValueError('method cannot be a non static class method')

        key = object()
        if not API._logLock:
            API._logKey = key

        return lambda *args, **kwargs: _API._wrappedMethod(key, method, *args, **kwargs)

    @property
    def patientList(self):
        return _API._dic["patientList"]

    @patientList.setter
    def patientList(self, patientList):
        _API._dic["patientList"] = patientList

        for cls in _API._apiClasses:
            cls.patientList = patientList

    @staticmethod
    def _convertArgToString(arg):
        argStr = ''

        if isinstance(arg, PatientList):
            argStr = 'API.patientList'
        elif isinstance(arg, Patient):
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
    def _log(cmd):
        scriptPath = os.path.join(str(Script.__path__[0]), 'API_log.py')
        with open(scriptPath, 'a') as f:
            f.write(cmd + '\n')

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
    def _wrappedMethod(key, method, *args, **kwargs):
        if not _API._logLock:
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

            callStr = method.__name__ + '(' + argsStr + ')'

            isFunction = True
            isstatic = True
            try:
                cls = get_class_that_defined_method(method)
                if not cls is None:
                    isstatic = isinstance(inspect.getattr_static(cls, method.__name__), staticmethod)
                    isFunction = False
            except:
                pass
            if isstatic and not isFunction:
                callStr = cls.__name__ + '.' + callStr
            elif not isstatic and not isFunction:
                raise ValueError('method cannot be a non static class method')

            if  _API._logging:
                _API._log(callStr)

        _logLock = True
        try:
            method(*args, **kwargs)
        except Exception as e:
            if _API._logLock and key==_API._logKey:
                _API._logLock = False
            raise(e)

        if _API._logLock and key == _API._logKey:
            _API._logLock = False

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
