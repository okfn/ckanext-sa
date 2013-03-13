import os
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.base as base


class SACustomizations(plugins.SingletonPlugin):
    plugins.implements(plugins.IRoutes)
    plugins.implements(plugins.IConfigurer, inherit=True)
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
        config['ckan.site_logo'] = '/images/sa_logo.png'
        config['ckan.favicon'] = '/images/sa_favicon.ico'

        toolkit.add_resource('theme/fanstatic_library', 'ckanext-sa')

    def before_map(self, route_map):
        route_map.connect('accessibility', '/accessibility',
                controller='ckanext.sa.plugin:SAController',
                action='accessibility')
        return route_map

    def after_map(self, route_map):
        return route_map

    def get_helpers(self):
        return {}


class SAController(base.BaseController):

    def accessibility(self):
        return base.render('accessibility.html')
