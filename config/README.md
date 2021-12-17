# Configuration

In this directory, create/modify your logging configuation file and argparse (function main.py) configuration file. Attention, command-line arguments override these parameters. Any new argument should be added to `parser.py`.


## Logging
If a logging configuration file is provided, it will load it and use it as logging config. Logging files follows a logging-specific template and have .json style syntax (eg. "key": "value"). The user can defines, the formatters, the handlers, the loggers and the filters to define an [advanced logging configuration](https://docs.python.org/3/howto/logging.html#advanced-logging-tutorial). If the user wishes to use [basic logging configuration](https://docs.python.org/3/howto/logging.html#basic-logging-tutorial), just specify the logging level (`DEBUG`,`INFO`,`WARNING`,`ERROR`,`CRITICAL`) on command-line. It will output the log messages in the console by defaults.

## Arguments

If a configuration file is provided, the parser will parse values from it and use those as the default values for the argparse arguments.

Config files can have .ini or .yaml style syntax (eg. key=value or key: value)

