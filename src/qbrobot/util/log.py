import logging

from  qbrobot import qsettings


try :
    from util import send_dingding 
except ImportError:
    DINGDING_CANUSE = False
else:
    DINGDING_CANUSE = True


"""
    class DingDingLogger 
    pass all args to logger.method, and call dingding.send_msg()
    1. debug message don't send to dingding.
    2. only send_msg( message ), can't pass multi args.
"""
class DingDingLogger:

    def __init__(self, logger = None ):
        self.logger = logger 


    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)
        if DINGDING_CANUSE:
            send_dingding.send_msg(msg, dingding_robot_id)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)
        if DINGDING_CANUSE:
            send_dingding.send_msg(msg, dingding_robot_id)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)
        if DINGDING_CANUSE:
            send_dingding.send_msg(msg, dingding_robot_id)

    def log(self, lvl, msg, *args, **kwargs):
        self.logger.log(lvl, msg, *args, **kwargs)
        if DINGDING_CANUSE:
            send_dingding.send_msg(msg, dingding_robot_id)

"""
handler = logging.handlers.RotatingFileHandler(str(logFile) + '.LOG', maxBytes = 1024 * 1024 * 500, backupCount = 5)
    fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)
    logger = logging.getLogger(str(logFile))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
"""


def setup_custom_logger():

    
    formatter = logging.Formatter(fmt=qsettings.LOG_FORMATTER)

    file_name = qsettings.LOG_FILE
    #file_name = None
    if file_name :
        handler = logging.FileHandler( file_name )
    else:
        handler = logging.StreamHandler()

    #handler = logging.StreamHandler()
    handler.setFormatter(formatter)


    #print('setup_custom_logger', name)
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(qsettings.LOG_LEVEL)

    return logger

    """
    if DINGDING_CANUSE :
        print('setup_custom_logger  dingding ')
        return  DingDingLogger( logger )
    else:
        return logger
        """

