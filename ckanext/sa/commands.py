from ckan.lib.cli import CkanCommand

import logging
logger = logging.getLogger()


class DataStore(CkanCommand):
    """
    Upload all resources from the FileStore to the DataStore

    Usage:

    paster datastore [package-id]
            - Update all resources or just those belonging to a specific
              package if a package id is provided.

    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 0
    max_args = 1
    MAX_PER_PAGE = 50

    def command(self):
        """
        Parse command line arguments and call the appropriate method
        """
        print "here"
