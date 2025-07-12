# Configuration

In this directory, create/modify your logging configuation file and argparse configuration file. Careful, command-line arguments override these parameters. Any new argument should be added to `parser.py`.


## Logging
If a logging configuration file is provided, it will load it and use it as logging config. Logging files follows a logging-specific template and have .json style syntax (eg. "key": "value"). The user can defines, the formatters, the handlers, the loggers and the filters to define an [advanced logging configuration](https://docs.python.org/3/howto/logging.html#advanced-logging-tutorial). If the user wishes to use [basic logging configuration](https://docs.python.org/3/howto/logging.html#basic-logging-tutorial), just specify the logging level (`DEBUG`,`INFO`,`WARNING`,`ERROR`,`CRITICAL`) on command-line. It will output the log messages in the console by defaults.

## Arguments 

If a configuration file is provided, the parser will parse values from it and use those as the default values for the argparse arguments.

Config files can have .ini or .yaml style syntax (eg. key=value or key: value)

## Examples
Run `main` without command-line arguments but with args (`main.conf`) and logging (`logging_config.json`) configuration files found in dir `config/`, `etc/`, `/usr/local/etc/` or `os.curdir` (*): 
```console
user@server:~$ python3 main.py
21/12/2021 09:38:01 AM - root - INFO - Loading logging configuration: config/logging_config.json
21/12/2021 09:38:01 AM - logConfigParser - INFO - Log level set: INFO
21/12/2021 09:38:01 AM - logConfigParser - INFO - Loading configuration: config/main.conf
21/12/2021 09:38:01 AM - logConfigParser - INFO - Option 1: config value 1
21/12/2021 09:38:01 AM - logConfigParser - INFO - Option 2: config value 2
21/12/2021 09:38:01 AM - __main__ - INFO - Start Application
```
Output `INFO` messages because log level is set to `INFO` in the logging config file. The output format was also specified in the file. Values for arguments `Option 1` and `Option 2` taken from the args config file.

Run `main` with command-line arguments:
```console
user@server:~$ python3 main.py -l debug -1 test
INFO:logConfigParser:Log level set: DEBUG
INFO:logConfigParser:Loading configuration: config/main.conf
INFO:logConfigParser:Option 1: test
INFO:logConfigParser:Option 2: config value 2
INFO:__main__:Start Application
DEBUG:__main__:Debugging test message
```
Command-line arguments override configuration files even if it is found. A basic logging configuration is used (simple formatting, we can specify the log level with command `-l`). 

If no configuration files found in dir (*) and `main` run without arguments:
```console
user@server:~$ python3 main.py
ERROR:root:Logging file config not found and log level not set (default). Specifify a logging level through command line
```
The user should at least define the log level she/he wants to configure basic logging.

Finally, the user can also set herself/himself a path to logging or ags config files:
```console
user@server:~$ python3 main.py -lc config/logging_config_test.json -c config/main_test.conf
21/12/2021 10:28:33 AM - root - INFO - Loading logging configuration: config/logging_config_test.json
21/12/2021 10:28:33 AM - logConfigParser - INFO - Log level set: INFO
21/12/2021 10:28:33 AM - logConfigParser - INFO - Loading configuration: config/main_test.conf
21/12/2021 10:28:33 AM - logConfigParser - INFO - Option 1: config value 1
21/12/2021 10:28:33 AM - logConfigParser - INFO - Option 2: config value 2
21/12/2021 10:28:33 AM - __main__ - INFO - Start Application
```


