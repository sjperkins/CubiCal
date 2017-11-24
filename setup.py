# CubiCal: a radio interferometric calibration suite
# (c) 2017 Rhodes University & Jonathan S. Kenyon
# http://github.com/ratt-ru/CubiCal
# This code is distributed under the terms of GPLv2, see LICENSE.md for details
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 SKA South Africa
#
# This file is part of CubeCal.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import logging
from pprint import pformat

from distutils.fancy_getopt import translate_longopt

from setuptools import setup, find_packages
from setuptools.extension import Extension
from setuptools.command.build_ext import build_ext

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
log = logging.getLogger()

def _setup_extensions():
  """
  Deferred extension creation.

  By this point, numpy and cython need to have been installed by pip/setuptools.
  """
  try:
    import numpy as np
  except ImportError:
    log.exception("Install cannot proceed without numpy")
    # Rethrow. We should *always* expect numpy install to succeed
    raise
  else:
    include_path = np.get_include()

  cmpl_args = ['-fopenmp',
               '-ffast-math',
               '-O2',
               '-march=native',
               '-mtune=native',
               '-ftree-vectorize']

  link_args = ['-lgomp']

  try:
    from Cython.Build import cythonize
    import Cython.Compiler.Options as CCO
  except ImportError:
    log.exception("Cython unavailable. Using bundled .c and .cpp files.")
    have_cython = False
  else:
    log.info("Cython is available. Cythonizing...")
    have_cython = True

  if have_cython:
    CCO.buffer_max_dims = 9

    extensions = (
        [Extension("cubical.kernels.cyfull_complex", ["cubical/kernels/cyfull_complex.pyx"],
            include_dirs=[include_path], extra_compile_args=cmpl_args, extra_link_args=link_args),
         Extension("cubical.kernels.cyphase_only", ["cubical/kernels/cyphase_only.pyx"],
            include_dirs=[include_path], extra_compile_args=cmpl_args, extra_link_args=link_args),
         Extension("cubical.kernels.cyfull_W_complex", ["cubical/kernels/cyfull_W_complex.pyx"],
            include_dirs=[include_path], extra_compile_args=cmpl_args, extra_link_args=link_args),
         Extension("cubical.kernels.cychain", ["cubical/kernels/cychain.pyx"],
            include_dirs=[include_path], extra_compile_args=cmpl_args, extra_link_args=link_args),
         Extension("cubical.kernels.cytf_plane", ["cubical/kernels/cytf_plane.pyx"],
            include_dirs=[include_path], language="c++", extra_compile_args=cmpl_args,
            extra_link_args=link_args),
         Extension("cubical.kernels.cyf_slope", ["cubical/kernels/cyf_slope.pyx"],
            include_dirs=[include_path], language="c++", extra_compile_args=cmpl_args,
            extra_link_args=link_args),
         Extension("cubical.kernels.cyt_slope", ["cubical/kernels/cyt_slope.pyx"],
            include_dirs=[include_path], language="c++", extra_compile_args=cmpl_args,
            extra_link_args=link_args)])

    return cythonize(extensions, compiler_directives={'binding': True})
  else:
    return (
        [Extension("cubical.kernels.cyfull_complex", ["cubical/kernels/cyfull_complex.c"],
            include_dirs=[include_path], extra_compile_args=cmpl_args, extra_link_args=link_args),
         Extension("cubical.kernels.cyphase_only", ["cubical/kernels/cyphase_only.c"],
            include_dirs=[include_path], extra_compile_args=cmpl_args, extra_link_args=link_args),
         Extension("cubical.kernels.cyfull_W_complex", ["cubical/kernels/cyfull_W_complex.c"],
            include_dirs=[include_path], extra_compile_args=cmpl_args, extra_link_args=link_args),
         Extension("cubical.kernels.cychain", ["cubical/kernels/cychain.c"],
            include_dirs=[include_path], extra_compile_args=cmpl_args, extra_link_args=link_args),
         Extension("cubical.kernels.cytf_plane", ["cubical/kernels/cytf_plane.cpp"],
            include_dirs=[include_path], extra_compile_args=cmpl_args, extra_link_args=link_args),
         Extension("cubical.kernels.cyf_slope", ["cubical/kernels/cyf_slope.cpp"],
            include_dirs=[include_path], extra_compile_args=cmpl_args, extra_link_args=link_args),
         Extension("cubical.kernels.cyt_slope", ["cubical/kernels/cyt_slope.cpp"],
            include_dirs=[include_path], extra_compile_args=cmpl_args, extra_link_args=link_args)])

def option_names(options):
    return [translate_longopt(n.rstrip("=")) for n,_,_ in options]

class BuildCommand(build_ext):
  _build_command_options = [('test=', None, "Test options")]
  user_options = _build_command_options + build_ext.user_options

  def initialize_options(self):
    """ Initialise custom options """

    # Initialise our user options
    for o in option_names(self._build_command_options):
      setattr(self, o, None)

    # Now defer to the parent which will initialise its own options
    build_ext.initialize_options(self)

  def run(self):
    """
    At this point pip will have installed our numpy and cython dependencies.
    initialize_options and finalize_options will already have been run...

    Now override run() to:
    * Save any options created on the object
    * Re-run self.initialize_options() to set custom options and self.extensions to None
    * Create custom extensions through _setup_extensions()
    * Re-run self.finalize_options() to run setuptools internal setup on the extensions.
    * Re-apply any options to the object
    """
    # Save this class's configured user options
    opt_names = option_names(self._build_command_options)
    saved_options = {o: getattr(self, o) for o in opt_names}

    # Save all user options for later sanity checks
    all_opt_names = option_names(self.user_options)
    pre_opts = {o: getattr(self, o) for o in all_opt_names}

    # Reset the build_ext options here
    # In particular this sets self.extensions to None
    self.initialize_options()

    try:
      # Override setup.py ext_modules with our actual extensions here
      self.distribution.ext_modules = _setup_extensions()
    except Exception:
      log.exception("Exception creating extensions")
      raise

    # Now re-run finalize options to re-create self.extensions
    self.finalize_options()

    # Re-apply any previously configured user options for this class
    for o, v in saved_options.items():
      setattr(self, o, v)

    # Test that custom option is correctly set
    assert self.test == 'test'

    # Now recover all options for sanity check with previous options
    post_opts = {o: getattr(self, o) for o in all_opt_names}

    if not pre_opts == post_opts:
        astr = pformat(pre_opts)
        nstr = pformat(post_opts)
        raise ValueError("Option mismatch\n"
                        "Before%s\n"
                        "After%s\n" % (astr, nstr))

    # Do the extension builds
    build_ext.run(self)

# Check for readthedocs environment variable.
on_rtd = os.environ.get('READTHEDOCS') == 'True'

if on_rtd:
    requirements = ['numpy',
                    'cython',
                    'futures',
                    'matplotlib',
                    'scipy']
else:
    requirements = ['numpy',
                    'cython',
                    'futures',
                    'python-casacore>=2.1.2',
                    'sharedarray',
                    'matplotlib',
                    'scipy',
                    'astro-tigger']

setup(name='cubical',
      version='0.9.2',
      description='Fast calibration implementation exploiting complex optimisation.',
      url='https://github.com/ratt-ru/Cubical',
      classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering :: Astronomy"],
      author='Jonathan Kenyon',
      author_email='jonosken@gmail.com',
      license='GNU GPL v3',
      cmdclass={'build_ext': BuildCommand},
      packages=['cubical', 'cubical.machines', 'cubical.tools', 'cubical.kernels'],
      install_requires=requirements,
      include_package_data=True,
      zip_safe=False,
      # Make a dummy module to force call to build_ext
      ext_modules = [Extension("DUMMY", [])],
      # Pass a test option through to build_ext
      options = {
                  'build_ext' : {
                    'test' : 'test'
                  }
                },
      entry_points={'console_scripts': ['gocubical = cubical.main:main']},
)