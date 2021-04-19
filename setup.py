#!/usr/bin/env python3
#from distutils.core import setup
from setuptools import setup

import re
with open("src/elnok/__init__.py") as f:
    text = f.read()

version = re.search("__version__ = \"(.*?)\"", text).groups()[0]


setup(name='elnok',
      version=version,
      packages=['elnok'],
      package_dir={'': 'src'},
      description='A light front-end to Logstash/Elasticsearch',
      author="Éric Piel",
      author_email="piel@delmic.com",
      url="https://github.com/delmic/elnok",
      entry_points={
          "console_scripts": [
              "elnok = elnok.__main__:main"
          ]
      }
)
