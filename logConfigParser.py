import sys
from argparse import ArgumentParser
from configparser import ConfigParser

import logging
import logging.config
import os
import json


LOGGING_CONFIG_FILE = 'logging_config.json'
CONFIG_FILE = 'main.conf'
CONFIG_LOCATIONS = ['etc',
                    '/usr/local/etc',
                    os.curdir,
                    'config/']

conf_locations = [ os.path.join(dir, CONFIG_FILE) \
                      for dir in reversed(CONFIG_LOCATIONS) ]

def _parse_args(args):
    # parse values from a configuration file if provided and use those as the
    # default values for the argparse arguments
    global CONFIG_LOCATIONS, CONFIG_FILE, LOGGING_CONFIG_FILE

    logging_argparse = ArgumentParser(prog=__file__, add_help=False)
    logging_argparse.add_argument('-l', '--log-level',
								  help='set log level',
                        		  choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'NOTSET'],
                        		  nargs   = '?',
                        		  const   = "INFO",
                        		  default = "NOTSET",
                        		  type    = str.upper)
    logging_argparse.add_argument('-lc', '--logging-config', dest='logging_config',
                        help='change default log file configuration',
                        default=None)
    logging_args, _ = logging_argparse.parse_known_args(args)

	# ----------------------------------------------------------
    # Configure logging 
    log_locations = [ os.path.join(dir, LOGGING_CONFIG_FILE) \
                      for dir in reversed(CONFIG_LOCATIONS) ]

    if logging_args.logging_config:
        log_locations.insert(0, logging_args.logging_config)
    loggingConfig = None
    for p in log_locations:
        if os.path.exists(p):
            loggingConfig = p

    if logging_args.log_level != 'NOTSET':
        # Command line config (basic config)
    	try:
    	    logging.basicConfig(level=logging_args.log_level)
    	except ValueError:
    	    logging.error("Invalid log level: {}".format(logging_args.log_level))
    	    sys.exit(1)
    else:
		# logging file config (advanced config)
        if loggingConfig:
            with open(loggingConfig,'r') as log_fid:
                config_dict = json.load(log_fid)
            logging.config.dictConfig(config_dict)
            logging.info('Loading logging configuration: {}'.format(loggingConfig))
        else:
            logging.error("Logging file config not found and log level not set (default). Specifify a logging level through command line")


    logger = logging.getLogger(__name__)
    logger.info("Log level set: {}"
                .format(logging.getLevelName(logger.getEffectiveLevel())))

    # ----------------------------------------------------------
    # parse values from a configuration file if provided and use those as the
    # default values for the argparse arguments
    config_argparse = ArgumentParser(prog=__file__, add_help=False)
    config_argparse.add_argument('-c', '--config-file', 
                        help='change default configuration location',
                        default=None)
    config_args, _ = config_argparse.parse_known_args(args)

    defaults = {
        'option1': "default value",
        'option2': "default value"
    }

    if config_args.config_file:
        conf_locations.insert(0, config_args.config_file)
    config = None
    for p in conf_locations:
        if os.path.exists(p):
            config = p
    if config:
        logger.info("Loading configuration: {}".format(config))
        try:
            config_parser = ConfigParser()
            with open(config) as f:
                config_parser.read_file(f)
            config_parser.read(config)
        except OSError as err:
            logger.error(str(err))
            sys.exit(1)
		# overide default values by file values
        defaults.update(dict(config_parser.items('options')))

    # parse the program's main arguments using the dictionary of defaults and
    # the previous parsers as "parent' parsers
    parsers = [logging_argparse, config_argparse]
    main_parser = ArgumentParser(prog=__file__, parents=parsers)
    main_parser.set_defaults(**defaults)
    # Dummy example
    main_parser.add_argument('-1', '--option1')
    main_parser.add_argument('-2', '--option2')
    main_args = main_parser.parse_args(args)

    # where did the value of each argument come from?
    logger.info("Option 1: {}".format(main_args.option1))
    logger.info("Option 2: {}".format(main_args.option2))

    return main_args
