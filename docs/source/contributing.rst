
===========================
Contributing to the project
===========================

We welcome contributions from all users to the project:

1. Documentation fixes/updates
2. Example notebooks to illustrate features/methods
3. Bug fixes
4. New code

However, we ask that contributors please follow these guidelines when contributing to the package. This allows us to retain some level of homogenerity throughout a project and will make it easiy to maintain and improve in the long run.

A list of current contributors can be found in the project root. 

1. Please ensure that all code follows the Python `Google Python Style Guide <https://google.github.io/styleguide/pyguide.html>`_ standard.
2. Please ensure that your code is well commented, so that programmers of varying abilities have a good chance in following it.
3. Please make sure that any code, or bug-fixes you contribute are accompanied by a `pytest <https://docs.pytest.org>`_.
4. Please run a full `pytest <https://docs.pytest.org>`_ prior to merging your code and ensure all tests pass (or that your new code has not caused any new test failures).
5. Please make sure that all modules, classes, functions (even private ones) have docstrings. This enables us to easily produce high quality documentation and improves the user experience. 
   This module uses Numpy docstrings for the most part. Please follow `this <https://developer.lsst.io/python/numpydoc.html>`_ excellent guide if unsure.
6. Any HOWTOs or extended user documentation should be written in `reStructuredText <https://docutils.sourceforge.io/rst.html>`_ (preferably) or `Markdown <https://en.wikipedia.org/wiki/Markdown>`_.
7. We incorporate Jupyter notebooks into the documentation, so please ensure they are fairly quick to run and do not have reams of output associated with them. Also, please make sure that all output is collapsed (removed) prior to committing the notebook to git.
8. Please make sure that any test data you submit is small and compressed and please do not commit any individual level data that is not already in the public domain.

If you want to contribute and are unsure on any of these points please `contact <amand.schmidt@ucl.ac.uk>`_ the lead developer. 

Many thanks in advance!


