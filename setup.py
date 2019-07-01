#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import os
import re
import sys

try:
    import pypandoc

    readme = pypandoc.convert("README.md", "rst")
except (IOError, ImportError):
    readme = ""

package = "tapioca_yadirect"


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    init_py = open(os.path.join(package, "__init__.py")).read()
    return re.search("^__version__ = ['\"]([^'\"]+)['\"]", init_py, re.MULTILINE).group(
        1
    )


# python setup.py register
if sys.argv[-1] == "publish":
    os.system("python setup.py sdist upload")
    args = {"version": get_version(package)}
    print("You probably want to also tag the version now:")
    print("  git tag -a %(version)s -m 'version %(version)s'" % args)
    print("  git push --tags")
    sys.exit()

setup(
    name="tapioca-yadirect",
    version=get_version(package),
    description="Yadirect API wrapper using tapioca",
    long_description=readme,
    author="Pavel Maksimov",
    author_email="vur21@ya.ru",
    url="https://github.com/pavelmaksimov/tapioca-yadirect",
    packages=["tapioca_yadirect"],
    package_dir={"tapioca_yadirect": "tapioca_yadirect"},
    include_package_data=True,
    install_requires=["pandas", "requests-oauthlib>=0.4.2"],
    license="BSD",
    zip_safe=False,
    keywords="tapioca-yadirect",
    test_suite="tests",
)
