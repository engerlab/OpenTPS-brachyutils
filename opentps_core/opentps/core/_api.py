import logging
import sys
from io import StringIO

logger = logging.getLogger(__name__)

class APIInterpreter:
    @staticmethod
    def run(code):
        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()

        try:
            exec(code)
        except Exception as err:
            sys.stdout = old_stdout
            logger.info(format(err))
            raise err from err

        sys.stdout = old_stdout
        return redirected_output.getvalue()
