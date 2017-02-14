#!/bin/bash

set -e

pip install praw
pip install nose
pip install coverage coveralls

python --version
python -c "import praw; print('praw %s' % praw.__version__)"
python setup.py build_ext --inplace
