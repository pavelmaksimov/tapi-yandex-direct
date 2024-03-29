#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import os
import re

with open("README.md", "r", encoding="utf8") as fh:
    readme = fh.read()

package = "tapi_yandex_direct"


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    init_py = open(os.path.join(package, "__init__.py")).read()
    return re.search("^__version__ = ['\"]([^'\"]+)['\"]", init_py, re.MULTILINE).group(
        1
    )


setup(
    name="tapi-yandex-direct",
    version=get_version(package),
    description="Python client for API Yandex Direct",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Pavel Maksimov",
    author_email="vur21@ya.ru",
    url="https://github.com/pavelmaksimov/tapi-yandex-direct",
    packages=[package],
    include_package_data=False,
    install_requires=["requests", "orjson", "tapi-wrapper2>=0.1.2,<1.0"],
    license="MIT",
    zip_safe=False,
    keywords="tapi,wrapper,yandex,metrika,api,direct,яндекс,директ,апи",
    test_suite="tests",
    package_data={
        package: ["*"],
    },
)
