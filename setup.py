import sys
from os import path
from os.path import join, dirname, abspath
from setuptools import setup, find_packages
from setuptools import Extension
from codecs import open

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

if sys.platform == 'win32':
    PLATFORM_EXTRAS = [
        'pywin32',
    ]
    extensions = None
else:
    from Cython.Build import cythonize

    PLATFORM_EXTRAS = [
        'cython',
        'posix_ipc',
    ]
    extensions = [Extension(
        'HybridLock',
        ["speedysvc/hybrid_lock/HybridLock.pyx"],
        libraries=[
            "rt",  # POSIX functions seem to require this
        ],
        library_dirs=[
            join(
                dirname(abspath(__file__)),
                "speedysvc/hybrid_lock"
            )
        ]
    )]

setup(
    name='speedysvc',
    version='0.1.0',
    description='Python client-server microservices using '
                'the fastest means possible - shared memory.',
    long_description=long_description,
    url='https://github.com/mcyph/speedysvc',
    author='Dave Morrissey',
    author_email='20507948+mcyph@users.noreply.github.com',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Networking',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Operating System :: POSIX :: Linux',
    ],

    keywords='mmap sockets',
    packages=find_packages(),
    ext_modules=None if extensions is None else cythonize(
        extensions,
        include_path=[join(dirname(abspath(__file__)), "speedysvc/hybrid_lock")],
        language_level=3
    ),
    install_requires=[
        'msgpack',
        #'python-snappy',
        'cherrypy',
        'jinja2',
        'psutil',
    ] + PLATFORM_EXTRAS,
    package_data = {
        '': ['*.json', '*.ini', '*.html'],
    },
    include_package_data=True,
    zip_safe=False
)
