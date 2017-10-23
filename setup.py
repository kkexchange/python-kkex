from distutils.core import setup
from setuptools import find_packages

setup(name='kkex',
      version='0.0.1',
      description='kkex client',
      author='Zeng Ke',
      author_email='superisaac.ke@gmail.com',
      packages=find_packages(),
      scripts=[],
      install_requires=[
          'requests'
      ]
)
