
from setuptools import setup, find_packages


__author__ = 'Mahmoud Hashemi and Stephen LaPorte'
__version__ = '0.0.1'
__contact__ = 'mahmoud@hatnote.com'
__url__ = 'https://github.com/hatnote/montage'
__license__ = 'BSD'


setup(name='hatnote-montage',
      version=__version__,
      description="A voting platform for WLM",
      long_description=__doc__,
      author=__author__,
      author_email=__contact__,
      url=__url__,
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      license=__license__,
      platforms='any',
      )

"""
TODO

A brief checklist for release:

* tox
* git commit (if applicable)
* Bump setup.py version off of -dev
* git commit -a -m "bump version for x.y.z release"
* python setup.py sdist bdist_wheel upload
* bump docs/conf.py version
* git commit
* git tag -a x.y.z -m "brief summary"
* write CHANGELOG
* git commit
* bump setup.py version onto n+1 dev
* git commit
* git push

"""
