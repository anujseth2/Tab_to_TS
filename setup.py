"""
Setup file for Tab_to_TS

=============================================================================
WHAT THIS FILE DOES:
=============================================================================
This file allows pip to install our project in "editable" mode.
Editable mode means changes to the code are immediately available
without needing to reinstall.

To install in editable mode, run:
    pip install -e .

=============================================================================
"""

from setuptools import setup, find_packages

setup(
    name="tab_to_ts",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.9",
)
