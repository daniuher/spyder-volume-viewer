# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © 2026, fried-pineapple0
#
# Licensed under the terms of the GNU General Public License v3
# ----------------------------------------------------------------------------
"""
VolumeViewer setup.
"""
from setuptools import find_packages
from setuptools import setup

from volumeviewer import __version__


setup(
    # See: https://setuptools.readthedocs.io/en/latest/setuptools.html
    name="volumeviewer",
    version=__version__,
    author="fried-pineapple0",
    author_email="spyder.python@gmail.com",
    description="Boilerplate needed to create a Spyder Plugin.",
    license="GNU General Public License v3",
    url="https://github.com/spyder-bot/volumeviewer",
    python_requires='>= 3.7',
    install_requires=[
        "qtpy",
        "qtawesome",
        "spyder>=5.0.1",
    ],
    packages=find_packages(),
    entry_points={
        "spyder.plugins": [
            "volumeviewer = volumeviewer.spyder.plugin:VolumeViewer"
        ],
    },
    classifiers=[
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering",
    ],
)
