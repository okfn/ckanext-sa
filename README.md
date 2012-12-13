# ckanext-sa

Custom CKAN extension for [data.sa.gov.au](http://data.sa.gov.au/)

## How to Install Locally for Development

1. Install CKAN from source.

2. Install ckanext-pdeu. Activate your CKAN virtual environment and:

        git clone git@github.com:okfn/ckanext-sa.git
        cd ckanext-sa
        python setup.py develop

3. Edit the following settings to the `[app:main]` section of your CKAN config
   file (e.g. `development.ini` or `sa.ini`):

        ckan.plugins = stats sa_customizations
        ckan.site_title = data.sa.gov.au
        ckan.site_description = South Australian Government Data Directory

4. Run CKAN, e.g. `paster serve sa.ini`

Note on CKAN versions: at the time of writing the `master` branch of
ckanext-sa is intended to work with CKAN 2.0 (currently the `master` branch
of ckan).