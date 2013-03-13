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
    max_content_length = int(config.get('ckanext-archiver.max_content_length',
        50000000))

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
                push_to_datastore(context, resource)
                break
            break


    def push_to_datastore(self, context, resource):
        result  = download(context, resource,
                self.max_content_length, self.DATA_FORMATS)
        content_type = result['headers'].get('content-type', '')\
                                        .split(';', 1)[0]  # remove parameters

        f = open(result['saved_file'], 'rb')
        table_sets = AnyTableSet.from_fileobj(f, mimetype=content_type, extension=resource['format'].lower())

        ##only first sheet in xls for time being
        row_set = table_sets.tables[0]
        offset, headers = headers_guess(row_set.sample)
        row_set.register_processor(headers_processor(headers))
        row_set.register_processor(offset_processor(offset + 1))
        row_set.register_processor(datetime_procesor())

        logger.info('Header offset: {0}.'.format(offset))

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
        logger.info('Guessed types: {0}'.format(guessed_types))
        row_set.register_processor(types_processor(guessed_types, strict=True))
        row_set.register_processor(stringify_processor())

        ckan_url = context['site_url'].rstrip('/')

        datastore_create_request_url = '%s/api/action/datastore_create' % (ckan_url)

        guessed_type_names = [TYPE_MAPPING[type(gt)] for gt in guessed_types]

        def send_request(data):
            request = {'resource_id': resource['id'],
                       'fields': [dict(id=name, type=typename) for name, typename in zip(headers, guessed_type_names)],
                       'records': data}
            response = requests.post(datastore_create_request_url,
                             data=json.dumps(request),
                             headers={'Content-Type': 'application/json',
                                      'Authorization': context['apikey']},
                             )
            check_response_and_retry(response, datastore_create_request_url, logger)

        # Delete any existing data before proceeding. Otherwise 'datastore_create' will
        # append to the existing datastore. And if the fields have significantly changed,
        # it may also fail.
        try:
            logger.info('Deleting existing datastore (it may not exist): {0}.'.format(resource['id']))
            response = requests.post('%s/api/action/datastore_delete' % (ckan_url),
                            data=json.dumps({'resource_id': resource['id']}),
                            headers={'Content-Type': 'application/json',
                                    'Authorization': context['apikey']}
                            )
            if not response.status_code or response.status_code not in (200, 404):
                # skips 200 (OK) or 404 (datastore does not exist, no need to delete it)
                logger.error('Deleting existing datastore failed: {0}'.format(get_response_error(response)))
                raise DatastorerException("Deleting existing datastore failed.")
        except requests.exceptions.RequestException as e:
            logger.error('Deleting existing datastore failed: {0}'.format(str(e)))
            raise DatastorerException("Deleting existing datastore failed.")

        logger.info('Creating: {0}.'.format(resource['id']))

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

        logger.info("There should be {n} entries in {res_id}.".format(n=count, res_id=resource['id']))

        ckan_request_url = ckan_url + '/api/action/resource_update'

        resource.update({
            'webstore_url': 'active',
            'webstore_last_updated': datetime.datetime.now().isoformat()
        })

        response = requests.post(
            ckan_request_url,
            data=json.dumps(resource),
            headers={'Content-Type': 'application/json',
                     'Authorization': context['apikey']})

        if response.status_code not in (201, 200):
            raise DatastorerException('Ckan bad response code (%s). Response was %s' %
                                 (response.status_code, response.content))
