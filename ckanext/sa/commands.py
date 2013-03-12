import json
from ckan.lib.cli import CkanCommand
import ckan.logic as logic
import ckan.model as model

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

    def _get_all_packages(self):
        page = 1
        context = {
            'model': model,
        }
        while True:
            data_dict = {
                'page': page,
                'limit': self.MAX_PER_PAGE,
            }
            packages = logic.get_action('current_package_list_with_resources')(
                                        context, data_dict)
            if not packages:
                raise StopIteration
            for package in packages:
                yield package
            page += 1

    def command(self):
        """
        Parse command line arguments and call the appropriate method
        """
        if self.args and self.args[0] in ['--help', '-h', 'help']:
            print Datastorer.__doc__
            return

        if self.args:
            cmd = self.args[0]
        self._load_config()
        user = logic.get_action('get_site_user')({'model': model,
                                            'ignore_auth': True}, {})
        packages = self._get_all_packages()
