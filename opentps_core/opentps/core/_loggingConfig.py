import sys
import logging
import logging.config
import os
import json

from opentps.core.utils.programSettings import ProgramSettings


class loggerConfig:
    def __init__(self):
        programSettings = ProgramSettings()

        self.loggingConfigFile = programSettings.loggingConfigFile
        self.configLocations = [os.path.join(programSettings.workspace, 'Config')]

    def configure(self):
        # Configure logging before any output
        # Set log level on the root logger via logging config file

        logLocations = [os.path.join(dir, 'logging_config.json') \
                        for dir in reversed(self.configLocations)]

        logLocations.append(self.loggingConfigFile)

        loggingConfig = None
        for p in reversed(logLocations):
            if os.path.exists(p):
                loggingConfig = p

        # logging file config (advanced config)
        if loggingConfig:
            with open(loggingConfig, 'r') as log_fid:
                configDict = json.load(log_fid)
            logging.config.dictConfig(configDict)
            logging.info('Loading logging configuration: {}'.format(loggingConfig))
        else:
            logging.error(
                "Logging file config not found and log level not set (default). Specifify a logging level through "
                "command line")

        logger = logging.getLogger(__name__)
        logger.info("Log level set: {}"
                    .format(logging.getLevelName(logger.getEffectiveLevel())))
