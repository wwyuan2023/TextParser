# -*- coding: utf-8 -*-

"""Setup textparser libarary."""

import os, sys
import pip

from distutils.version import LooseVersion
from setuptools import find_packages
from setuptools import setup


if LooseVersion(sys.version) < LooseVersion("3.6"):
    raise RuntimeError(
        "textparser requires Python>=3.6, "
        "but your Python is {}".format(sys.version))

requirements = {
    "install": [
        "setuptools>=38.5.1",
        "numpy",
        "zhconv",
        "numba",
    ],
    "setup": [],
    "test": []
}
entry_points = {
    "console_scripts": [
        "text-parser=textparser.parser:main",
        "text-normalizer=textparser.modules.textnormalizer:main",
        "text-segmenter=textparser.modules.segmenter:main",
        "text-pronunciation=textparser.modules.pronunciation:main",
        "text-vectorization=textparser.modules.vectorization:main",
    ]
}

install_requires = requirements["install"]
setup_requires = requirements["setup"]
tests_require = requirements["test"]
extras_require = {k: v for k, v in requirements.items()
                  if k not in ["install", "setup"]}

dirname = os.path.dirname(__file__)
setup(name="textparser",
      version="0.1.5",
      url="https://github.com/wwyuan2023/TextParser.git",
      author="Wuwen YUAN",
      author_email="yuanwuwen@126.com",
      description="A python module for Chinese and English text analysis.",
      long_description=open(os.path.join(dirname, "README.md"), encoding="utf-8").read(),
      long_description_content_type="text/markdown",
      license="MIT License",
      packages=find_packages(include=["textparser*"]),
      install_requires=install_requires,
      setup_requires=setup_requires,
      tests_require=tests_require,
      extras_require=extras_require,
      entry_points=entry_points,
      include_package_data=True,
      classifiers=[
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: 3.8",
          "Programming Language :: Python :: 3.9",
          "Programming Language :: Python :: 3.10",
          "Programming Language :: Python :: 3.11",
          "Intended Audience :: Science/Research",
          "Operating System :: POSIX :: Linux",
          "License :: OSI Approved :: MIT License",
          "Topic :: Software Development :: Libraries :: Python Modules"],
      )
