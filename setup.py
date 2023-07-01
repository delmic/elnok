#!/usr/bin/env python3
#from distutils.core import setup
import os
import subprocess
import sys

from setuptools import setup

import re
with open("src/elnok/__init__.py") as f:
    text = f.read()

VERSION = re.search("__version__ = \"(.*?)\"", text).groups()[0]


# almost copy from elnok.__init__.py, but we cannot load it as it's not installed yet
def _get_version_git():
    """
    Get the version via git
    raises LookupError if no version info found
    """
    # change directory to root
    rootdir = os.path.dirname(__file__)

    try:
        out = subprocess.check_output(
            args=["git", "describe", "--tags", "--dirty", "--always"], cwd=rootdir
        )

        return out.strip().decode("utf-8")
    except EnvironmentError:
        raise LookupError("Unable to run git")


# Check version
try:
    gver = _get_version_git()
    if "-" in gver:
        sys.stderr.write("Warning: packaging a non-tagged version: %s\n" % gver)
    if VERSION != gver:
        sys.stderr.write(
            "Warning: package version and git version don't match:" " %s <> %s\n" % (VERSION, gver)
        )
except LookupError:
    pass


with open("requirements.txt") as f:
    required = f.read().splitlines()


setup(name='elnok',
      version=VERSION,
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
      },
      license="GPL-2",
      platforms="Linux",
      # For building the debian package we specify the dependencies in control file (Depends:)
      # hence the install_requires is commented out
      # uncomment it if you want to install the package with pip
      # install_requires=required,
)
