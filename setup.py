from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
	name='ckanext-sa',
	version=version,
	description="CKAN extension for data.sa.gov.au",
	long_description="""\
	""",
	classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
	keywords='',
	author='okfn',
	author_email='info@okfn.org',
	url='',
	license='',
	packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
	namespace_packages=['ckanext', 'ckanext.sa'],
	include_package_data=True,
	zip_safe=False,
	install_requires=[
		# -*- Extra requirements: -*-
	],
	entry_points=\
	"""
	[paste.paster_command]
	datastore_upload = ckanext.sa.commands:AddToDataStore

	[ckan.plugins]
	# Add plugins here
	sa_customizations=ckanext.sa.plugin:SACustomizations
	""",
)
