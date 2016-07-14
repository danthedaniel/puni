from setuptools import setup

setup(name='puni',
      version='0.3.0',
      description='Python UserNotes Interface for reddit',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Utilities'
      ],
      url='http://github.com/teaearlgraycold/puni',
      author='teaearlgraycold',
      license='GPLv3',
      packages=['puni'],
      install_requires=[
        'praw>=3.2.0',
      ],tests_require = [
        'nose',
      ],
      test_suite="nose.collector",
      zip_safe=False)
