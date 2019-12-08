"""A setuptools based setup module.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

from setuptools import setup, find_packages
from setuptools import Extension
from Cython.Build import cythonize
from codecs import open
from os import path
from os.path import join, dirname, abspath

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()


extensions = [Extension(
    'hybrid_spin_semaphore', [
        "network_tools/hybrid_spin_semaphore/hybrid_spin_semaphore.pyx",
    ],

    libraries=[
        "rt", # POSIX functions might require this?
        #"shared_mutex",
        #"errno", # errno, ENOENT
        #"fcntl", # O_RDWR, O_CREATE
        #"linux/limits", # NAME_MAX
        #"sys/mman", # shm_open, shm_unlink, mmap, munmap,
                      # PROT_READ, PROT_WRITE, MAP_SHARED, MAP_FAILED
        #"unistd", # ftruncate, close
        #"stdio", # perror
        #"stdlib", # malloc, free
        #"string", # strcpy
    ],
    library_dirs=[
        join(
            dirname(abspath(__file__)),
            "network_tools/hybrid_spin_semaphore"
        )
    ]
)]

#

setup(
    name='network_tools',
    version='0.1.0',
    description='Send/receive client/server classes which use sockets across networks, or high-performance mmap',
    long_description=long_description,
    url='https://github.com/jiyiiy/network_tools',
    author='David Morrissey',
    author_email='david.l.morrissey@gmail.com',

    classifiers=[  # Optional
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',

        # Pick your license as you wish
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        # 'Programming Language :: Python :: 3',
        # 'Programming Language :: Python :: 3.4',
        # 'Programming Language :: Python :: 3.5',
        # 'Programming Language :: Python :: 3.6',
    ],

    keywords='mmap sockets',
    packages=find_packages(),
    ext_modules=cythonize(
        extensions,
        include_path=[join(dirname(abspath(__file__)), "network_tools/hybrid_spin_semaphore")],
        language_level=3
    ),

    install_requires=[
        'msgpack',
        'setproctitle',
        'dataclasses',

        'matplotlib',
        'pyarrow',
        'python-snappy',
    ],

    zip_safe=True
)
