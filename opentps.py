
#This file is required by the build system to create the opentps package

# Modules to export in openTPS package
import Core
import GUI

import main
from Core import API
from Core.Data import PatientList

patientList = PatientList()
API.patientList = patientList

def run():
    main.main()


if __name__ == '__main__':
    run()