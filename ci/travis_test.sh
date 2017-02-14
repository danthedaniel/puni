#!/bin/bash

set -e

python --version
python -c "import praw; print('praw %s' % praw.__version__)"
nosetests -sv --with-coverage test.py
