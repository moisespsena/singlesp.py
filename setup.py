from distutils.cmd import Command
import os
import re
import sys
import shutil

from setuptools import setup, find_packages


THIS_PATH = os.path.abspath(os.path.realpath(os.path.dirname(__file__)))


def pkg_by_version(name=""):
    return name + ("" if sys.version_info[0] < 3 else "3")


def read(fname):
    with open(os.path.join(THIS_PATH, fname)) as f:
        return f.read()


class CleanCommand(Command):
    user_options = []

    def initialize_options(self):
        self.paths = []

        for f in os.listdir(THIS_PATH):
            if re.search("(^(build|dist|__pycache__|\.eggs)$|\.egg-info)", f):
                self.paths.append(f)

        for root, dirs, files in os.walk(THIS_PATH):
            for f in files:
                if f.endswith(".pyc") or f.endswith(".pyc") or \
                        f.endswith(".pyo"):
                    self.paths.append(os.path.join(root, f))

            for f in dirs:
                if re.search("^(__pycache__)$", f):
                    self.paths.append(os.path.join(root, f))

    def finalize_options(self):
        pass

    def run(self):
        for p in self.paths:
            if os.path.exists(p):
                if os.path.isdir(p):
                    print("Remove directory: " + p)
                    shutil.rmtree(p)
                else:
                    print("Remove file     : " + p)
                    os.unlink(p)


setup(
    name="singlesp",
    version='1.0.0',
    author="Moises P. Sena",
    author_email="moisespsena@gmail.com",
    description="Simple uses for Python subproccess module",
    license="MIT",
    keywords="system proc subprocess",
    url="https://github.com/moisespsena/singlesp.py",
    packages=find_packages(),
    long_description=read('README.rst'),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Utilities",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
    ],
    cmdclass={'clean': CleanCommand},
)