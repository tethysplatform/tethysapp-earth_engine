from setuptools import setup, find_namespace_packages
from tethys_apps.app_installation import find_resource_files

# -- Apps Definition -- #
app_package = 'earth_engine'
release_package = 'tethysapp-' + app_package

# -- Python Dependencies -- #
dependencies = []

# -- Get Resource File -- #
resource_files = find_resource_files('tethysapp/' + app_package + '/templates', 'tethysapp/' + app_package)
resource_files += find_resource_files('tethysapp/' + app_package + '/public', 'tethysapp/' + app_package)

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name=release_package,
    version='1.0.0',
    description='A Google Earth Engine demonstration Tethys App.',
    long_description=long_description,
    author='Nathan Swain',
    author_email='nswain@aquaveo.com',
    url='',  # The URL will be set in a future step.
    license='BSD 3-Clause',
    packages=find_namespace_packages(),
    package_data={'': resource_files},
    include_package_data=True,
    zip_safe=False,
    install_requires=dependencies,
)
