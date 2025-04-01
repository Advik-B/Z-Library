# setup.py
from setuptools import setup, find_packages
import os

# Read version from __init__.py
def get_version(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, rel_path), 'r') as fp:
        for line in fp.read().splitlines():
            if line.startswith('__version__'):
                delim = '"' if '"' in line else "'"
                return line.split(delim)[1]
    raise RuntimeError("Unable to find version string.")

# Read requirements from requirements.txt
def get_requirements(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, rel_path), 'r') as fp:
        return [
            line.strip() for line in fp.readlines()
            if not line.startswith('#') and 'rich' not in line
        ]

# Read README for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='zlibrary-sync',
    version=get_version('zlibrary/__init__.py'),
    author='Advik',
    author_email='<advik.b@gmail.com>',
    description='A synchronous Python library for interacting with Z-Library (unofficial).',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Advik-B/z-library',
    packages=find_packages(exclude=["tests*"]),
    install_requires=get_requirements('requirements.txt'),
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP",
        "Typing :: Typed",
    ],
    python_requires='>=3.7',
    # Include the py.typed file
    package_data={
        # IMPORTANT: Use the actual package directory name here
        'zlibrary': ['py.typed'],
    },
    include_package_data=True,
    options={'bdist_wheel':{'universal':True}}
)