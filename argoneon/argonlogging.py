import logging
import sys

LOGGING_FILE ='/var/log/argoneon.log'
FORMAT_STRING='%(asctime)s %(process)d [%(levelname)s] %(message)s'
DATE_FORMAT='%b %d %y %H:%M:%S'
#
#
#
def enableLogging( enableDebug : bool = False , logfile = LOGGING_FILE):
    if enableDebug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    if logfile == 'stdout':
        logging.basicConfig( stream=sys.stdout,
                             level=level,
                             format=FORMAT_STRING,
                             datefmt=DATE_FORMAT)
    else:
        logging.basicConfig( filename=logfile,
                             filemode='a',
                             level=level,
                             format=FORMAT_STRING,
                             datefmt=DATE_FORMAT)

#
#
#
def logDebug( message ):
    logging.debug( message )

#
#
#
def logInfo( message ):
    logging.info( message )

#
#
#
def logWarning( message ):
    logging.warning( message )

#
#
#
def logError( message ):
    logging.error( message )

