from pylons import config
from ckan.lib.cli import CkanCommand
import ckan.logic as logic
import ckan.model as model
from fetch_resource import download

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

    DATA_FORMATS = [
        'csv',
        'tsv',
        'text/csv',
        'txt',
        'text/plain',
        'text/tsv',
        'text/tab-separated-values',
        'xls',
        'application/ms-excel',
        'application/vnd.ms-excel',
        'application/xls',
        'application/octet-stream',
        'text/comma-separated-values',
        'application/x-zip-compressed',
        'application/zip',
    ]

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
            print Datastore.__doc__
            return

        if self.args:
            cmd = self.args[0]
        self._load_config()
        user = logic.get_action('get_site_user')({'model': model,
                                            'ignore_auth': True}, {})
        packages = self._get_all_packages()
        context = {
            'site_url': config['ckan.site_url'],
            'username': user.get('name'),
            'webstore_url': config.get('ckan.webstore_url')
        }
        max_content_length = int(config.get('ckanext-archiver.max_content_length', 50000000))
        for package in packages:
            for resource in package.get('resources', []):
                mimetype = resource['mimetype']
                if mimetype and (mimetype not in self.DATA_FORMATS
                        or resource['format'].lower() not in
                        self.DATA_FORMATS):
                    logger.warn('Skipping resource {0} from package {1} '
                            'because MIME type {2} or format {3} is '
                            'unrecognized'.format(resource['url'],
                            package['name'], mimetype, resource['format']))
                    continue
                logger.info('Datastore resource from resource {0} from '
                            'package {0}'.format(resource['url'],
                                                 package['name']))
                # TODO: update resource with datastore URL
                downloaded_resource = download(context, resource,
                        max_content_length, self.DATA_FORMATS)
                print downloaded_resource
                break
            break


    def push_to_datastore(self):
        # TODO: delete resource from datastore
        # TODO: upload to datastore
        pass


