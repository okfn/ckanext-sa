import datetime
import itertools
import messytables
from messytables import (AnyTableSet, types_processor, headers_guess,
                         headers_processor, type_guess, offset_processor)
from pylons import config
from ckan.lib.cli import CkanCommand
import ckan.logic as logic
import ckan.model as model
from fetch_resource import download

import logging
log = logging.getLogger()

TYPE_MAPPING = {
    messytables.types.StringType: 'text',
    # 'int' may not be big enough,
    # and type detection may not realize it needs to be big
    messytables.types.IntegerType: 'numeric',
    messytables.types.FloatType: 'float',
    messytables.types.DecimalType: 'numeric',
    messytables.types.DateType: 'timestamp',
    messytables.types.DateUtilType: 'timestamp'
}


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


class DatastorerException(Exception):
    pass


class AddToDataStore(CkanCommand):
    """
    Upload all resources with a url and a mimetype/format matching allowed
    formats to the DataStore

    Usage:

    paster datastore_upload
            - Update all resources.
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 0
    max_args = 1
    MAX_PER_PAGE = 50
    max_content_length = int(config.get('ckanext-archiver.max_content_length',
                             50000000))

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
            print self.__doc__
            return

        self._load_config()
        user = logic.get_action('get_site_user')({'model': model,
                                                 'ignore_auth': True}, {})
        packages = self._get_all_packages()
        context = {
            'username': user.get('name'),
            'user': user.get('name'),
            'model': model

        }
        for package in packages:
            for resource in package.get('resources', []):
                mimetype = resource['mimetype']
                if mimetype and not(mimetype in DATA_FORMATS or
                                    resource['format'].lower()
                                    in DATA_FORMATS):
                    log.warn('Skipping resource {0} from package {1} because '
                             'MIME type {2} or format {3} is '
                             'unrecognized'.format(resource['url'],
                                                   package['name'],
                                                   mimetype,
                                                   resource['format'])
                             )
                    continue
                log.info('Datastore resource from resource {0} from '
                         'package {0}'.format(resource['url'],
                                              package['name']))
                self.push_to_datastore(context, resource)

    def push_to_datastore(self, context, resource):
        try:
            result = download(
                context,
                resource,
                self.max_content_length,
                DATA_FORMATS
            )
        except Exception as e:
            log.exception(e)
            return
        content_type = result['headers'].get('content-type', '')\
                                        .split(';', 1)[0]  # remove parameters

        f = open(result['saved_file'], 'rb')
        table_sets = AnyTableSet.from_fileobj(
            f,
            mimetype=content_type,
            extension=resource['format'].lower()
        )

        ##only first sheet in xls for time being
        row_set = table_sets.tables[0]
        offset, headers = headers_guess(row_set.sample)
        row_set.register_processor(headers_processor(headers))
        row_set.register_processor(offset_processor(offset + 1))
        row_set.register_processor(datetime_procesor())

        log.info('Header offset: {0}.'.format(offset))

        guessed_types = type_guess(
            row_set.sample,
            [
                messytables.types.StringType,
                messytables.types.IntegerType,
                messytables.types.FloatType,
                messytables.types.DecimalType,
                messytables.types.DateUtilType
            ],
            strict=True
        )
        log.info('Guessed types: {0}'.format(guessed_types))
        row_set.register_processor(types_processor(guessed_types, strict=True))
        row_set.register_processor(stringify_processor())

        guessed_type_names = [TYPE_MAPPING[type(gt)] for gt in guessed_types]

        def send_request(data):
            data_dict = {
                'resource_id': resource['id'],
                'fields': [dict(id=name, type=typename) for name, typename
                           in zip(headers, guessed_type_names)],
                'records': data
            }
            response = logic.get_action('datastore_create')(
                context,
                data_dict
            )
            return response

        # Delete any existing data before proceeding. Otherwise
        # 'datastore_create' will append to the existing datastore. And if the
        # fields have significantly changed, it may also fail.
        log.info('Deleting existing datastore (it may not exist): '
                 '{0}.'.format(resource['id']))
        try:
            logic.get_action('datastore_delete')(
                context,
                {'resource_id': resource['id']}
            )
        except Exception as e:
            log.exception(e)

        log.info('Creating: {0}.'.format(resource['id']))

        # generates chunks of data that can be loaded into ckan
        # n is the maximum size of a chunk
        def chunky(iterable, n):
            it = iter(iterable)
            while True:
                chunk = list(
                    itertools.imap(
                        dict, itertools.islice(it, n)))
                if not chunk:
                    return
                yield chunk

        count = 0
        for data in chunky(row_set.dicts(), 100):
            count += len(data)
            send_request(data)

        log.info("There should be {n} entries in {res_id}.".format(
            n=count,
            res_id=resource['id']
        ))

        resource.update({
            'webstore_url': 'active',
            'webstore_last_updated': datetime.datetime.now().isoformat()
        })

        logic.get_action('resource_update')(context, resource)


def stringify_processor():
    def to_string(row_set, row):
        for cell in row:
            if not cell.value:
                cell.value = None
            else:
                cell.value = unicode(cell.value)
        return row
    return to_string


def datetime_procesor():
    ''' Stringifies dates so that they can be parsed by the db
    '''
    def datetime_convert(row_set, row):
        for cell in row:
            if isinstance(cell.value, datetime.datetime):
                cell.value = cell.value.isoformat()
                cell.type = messytables.StringType()
        return row
    return datetime_convert
