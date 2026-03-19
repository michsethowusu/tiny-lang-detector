from setuptools import setup, find_packages

setup(
    name="tiny-lang-detector",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "tiny-detect=src.cli:main",
        ],
    },
)
