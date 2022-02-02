"""
This is an example on how to use the startScriptfile to launch commands at the start of the program.
This can be used for example to automatically load data such as a CT image and it's contours.
It is particularly useful when the user needs to test a lot of times something with the same preparation (the same data for example).

We are here in the Script folder, when you can see an API_log.py file.
This file will contain each command that the user will execute using the program Graphical User Interface.
To save some commands to execute automatically at the next program start, the user has to:
- Use the program normally to first do manually the sequence of actions you would like to save.
- Create an empty startScript.py file in the Script folder
- Copy the content of the API_log.py file in the new startScript.py file (only the commands you want to keep, this file is not emptied automaticaly)
- Save the file (usually automatic)
- Close and relaunch the program

You should always copy the line:
from API.api import API

Here under are some examples
"""


# ------- Simple load data example --------
from API.api import API
API.loadData(['/home/damien/Desktop/Patient0/Patient0_dynSeq.p'])


# ------- Other examples ---------------
#TODO