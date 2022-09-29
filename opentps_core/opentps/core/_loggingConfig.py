import sys
import logging
import logging.config
import os
import json

from argparse import ArgumentParser
from configparser import ConfigParser

import opentps.core.config.logger as loggerModule

LOGGING_CONFIG_FILE = os.path.join(loggerModule.__path__[0], 'logging_config.json')
CONFIG_FILE = os.path.join(loggerModule.__path__[0], 'main.conf')
CONFIG_LOCATIONS = ['etc',
                    '/usr/local/etc',
                    os.curdir,
                    'config/']

confLocations = [ os.path.join(dir, CONFIG_FILE) \
                      for dir in reversed(CONFIG_LOCATIONS) ]

def configure(*args):
    # Configure logging before any output 
    # Set log level on the root logger either via command line or logging config file 
    global CONFIG_LOCATIONS, CONFIG_FILE, LOGGING_CONFIG_FILE

    loggingArgparse = ArgumentParser(prog=__file__, add_help=False)
    loggingArgparse.add_argument('-l', '--log-level',
								  help='set log level',
                        		  choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'NOTSET'],
                        		  nargs   = '?',
                        		  const   = "INFO",
                        		  default = "NOTSET",
                        		  type    = str.upper)
    loggingArgparse.add_argument('-lc', '--logging-config', dest='logging_config',
                        help='change default log file configuration',
                        default=None)
    loggingArgs, _ = loggingArgparse.parse_known_args(*args)

    logLocations = [ os.path.join(dir, LOGGING_CONFIG_FILE) \
                      for dir in reversed(CONFIG_LOCATIONS) ]

    if loggingArgs.logging_config:
        logLocations.insert(0, loggingArgs.logging_config)
    loggingConfig = None
    for p in logLocations:
        if os.path.exists(p):
            loggingConfig = p

    if loggingArgs.log_level != 'NOTSET':
        # Command line config (basic config)
    	try:
    	    logging.basicConfig(level=loggingArgs.log_level)
    	except ValueError:
    	    logging.error("Invalid log level: {}".format(loggingArgs.log_level))
    	    sys.exit(1)
    else:
		# logging file config (advanced config)
        if loggingConfig:
            with open(loggingConfig,'r') as log_fid:
                configDict = json.load(log_fid)
            logging.config.dictConfig(configDict)
            logging.info('Loading logging configuration: {}'.format(loggingConfig))
        else:
            logging.error("Logging file config not found and log level not set (default). Specifify a logging level through command line")


    logger = logging.getLogger(__name__)
    logger.info("Log level set: {}"
                .format(logging.getLevelName(logger.getEffectiveLevel())))

    # parse values from a configuration file if provided and use those as the
    # default values for the argparse arguments
    configArgparse = ArgumentParser(prog=__file__, add_help=False)
    configArgparse.add_argument('-c', '--config-file', 
                        help='change default configuration location',
                        default=None)

    configArgs, _ = configArgparse.parse_known_args(*args)

    defaults = {
        'option1': "default value",
        'option2': "default value"
    }

    if configArgs.config_file:
        confLocations.insert(0, configArgs.config_file)
    config = None
    for p in confLocations:
        if os.path.exists(p):
            config = p
    if config:
        logger.info("Loading configuration: {}".format(config))
        try:
            configParser = ConfigParser()
            with open(config) as f:
                configParser.read_file(f)
            configParser.read(config)
        except OSError as err:
            logger.error(str(err))
            sys.exit(1)
		# overide default values by file values
        defaults.update(dict(configParser.items('options')))

    # parse the program's main arguments using the dictionary of defaults and
    # the previous parsers as "parent' parsers
    parsers = [loggingArgparse, configArgparse]
    mainParser = ArgumentParser(prog=__file__, parents=parsers, exit_on_error=False)
    mainParser.set_defaults(**defaults)
    # Dummy example
    mainParser.add_argument('-1', '--option1')
    mainParser.add_argument('-2', '--option2')

    try:
        mainArgs = mainParser.parse_args(*args)
        # where did the value of each argument come from?
        logger.info("Option 1: {}".format(mainArgs.option1))
        logger.info("Option 2: {}".format(mainArgs.option2))

        return mainArgs

    except:
        return None

if __name__=='__main__':
    configure()