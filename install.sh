#!/bin/sh

PYTHON_IMPLEMENTATION="$(python -c 'import platform; print(platform.python_implementation())')"
rm -rf build/
tr '\n' '\0' < uninstall_files_${PYTHON_IMPLEMENTATION}.txt | xargs -0 rm -f --
python3 setup.py install --force --record uninstall_files_${PYTHON_IMPLEMENTATION}.txt
