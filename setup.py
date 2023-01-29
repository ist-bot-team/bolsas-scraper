#!/usr/bin/env python

from setuptools import setup

setup(
    name='bolsas-scraper',
    version='0.1.0',
    py_modules=['scraper'],
    entry_points={
        'console_scripts': ['bolsas-scraper = scraper:main']
    },
)
