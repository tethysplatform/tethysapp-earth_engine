from setuptools import setup, find_namespace_packages
from tethys_apps.app_installation import find_all_resource_files
from tethys_apps.base.app_base import TethysAppBase

# -- Apps Definition -- #
app_package = 'earth_engine'
release_package = f'{TethysAppBase.package_namespace}-{app_package}'

# -- Python Dependencies -- #
dependencies = []

# -- Get Resource File -- #
resource_files = find_all_resource_files(app_package, TethysAppBase.package_namespace)

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name=release_package,
    version='1.0.0',
    description='A Google Earth Engine demonstration Tethys App.',
    long_description=long_description,
    author='Luke Skywalker',
    author_email='lskywalker@example.com',
    url='',
    license='BSD-3-Clause',
    packages=find_namespace_packages(),
    package_data={'': resource_files},
    include_package_data=True,
    zip_safe=False,
    install_requires=dependencies,
)