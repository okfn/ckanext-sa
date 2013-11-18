import os

import routes.mapper

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.base as base

import ckan.new_authz as authz

def organization_datasets_show(org_id):
    '''Return a list of an organization's datasets.

    Returns a list of dataset dicts.

    organization_show() already returns the organization's datasets in the
    organization dict, but these are in a different order to on the
    organization's page (which uses a package_search() to get the datasets).

    This method uses a package_search() to get the datasets in the same order
    as on the organization's page.

    This is a workaround for <https://github.com/okfn/ckan/issues/860>

    '''
    data_dict = {
            'sort': None,
            'fq': '',
            'rows': 20,
            'facet.field': ['organization', 'groups', 'tags', 'res_format',
                'license_id'],
            'q': u' owner_org:"{org_id}"'.format(org_id=org_id),
            'start': 0,
            'extras': {},
            }
    response = toolkit.get_action('package_search')(data_dict=data_dict)
    return response['results']


def organization_show(name):
    '''Return the organization dict for the given organization.'''
    return toolkit.get_action('organization_show')(data_dict={'id': name})


def am_sysadmin():
    user_name = toolkit.c.user
    return authz.is_sysadmin(user_name)


class SACustomizations(plugins.SingletonPlugin):
    plugins.implements(plugins.IRoutes)
    plugins.implements(plugins.IConfigurer, inherit=True)
    plugins.implements(plugins.IConfigurable, inherit=True)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)

    def update_config(self, config):
        here = os.path.dirname(__file__)
        rootdir = os.path.dirname(os.path.dirname(here))

        our_public_dir = os.path.join(rootdir, 'ckanext', 'sa', 'theme',
                'public')
        template_dir = os.path.join(rootdir, 'ckanext', 'sa', 'theme',
                'templates')
        config['extra_public_paths'] = ','.join([our_public_dir,
                config.get('extra_public_paths', '')])
        config['extra_template_paths'] = ','.join([template_dir,
                config.get('extra_template_paths', '')])
        config['ckan.site_logo'] = '/data.sa_logo.png'
        config['ckan.favicon'] = '/images/sa_favicon.ico'

        toolkit.add_resource('theme/fanstatic_library', 'ckanext-sa')

    def configure(self, config):
        # Add the list of 'featured organizations' from the ini file to the
        # Jinja template environment.
        featured_orgs = config.get('ckan.featured_organizations', '')
        featured_orgs = [org.strip() for org in featured_orgs.split(',')
                if org]
        jinja_env = config['pylons.app_globals'].jinja_env
        jinja_env.globals['featured_orgs'] = featured_orgs

    def before_map(self, route_map):
        with routes.mapper.SubMapper(route_map,
                controller='ckanext.sa.plugin:SAController') as m:
            m.connect('accessibility', '/accessibility',
                    action='accessibility')
            m.connect('disclaimer', '/disclaimer', action='disclaimer')
            m.connect('privacy', '/privacy', action='privacy')
            m.connect('termsandconditions', '/termsandconditions',
                    action='termsandconditions')
            m.connect('contact', '/contact', action='contact')
            m.connect('copyright', '/copyright', action='copyright')
        return route_map

    def after_map(self, route_map):
        return route_map

    def get_helpers(self):
        return {'organization_show': organization_show,
                'organization_datasets_show': organization_datasets_show,
                'am_sysadmin': am_sysadmin,
               }


class SAController(base.BaseController):

    def accessibility(self):
        return base.render('accessibility.html')

    def disclaimer(self):
        return base.render('disclaimer.html')

    def privacy(self):
        return base.render('privacy.html')

    def termsandconditions(self):
        return base.render('termsandconditions.html')

    def contact(self):
        return base.render('contact.html')

    def copyright(self):
        return base.render('copyright.html')
