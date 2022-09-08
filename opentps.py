
#This file is required by the build system to create the opentps package

# Modules to export in openTPS package
import Core
import GUI

from Core import API
from Core.Data import PatientList

patientList = PatientList()
API.patientList = patientList

def run():
    # import main in run so that GUI classes are not imported if user does not launch it
    import main
    main.main()


if __name__ == '__main__':
    run()