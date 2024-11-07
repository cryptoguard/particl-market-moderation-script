from setuptools import setup, find_packages

setup(
    name="particl_moderation",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "rich==10.16.2",
        "prompt_toolkit==3.0.36",
        "PyYAML==6.0.1",
    ],
    entry_points={
        "console_scripts": [
            "particl-moderation=particl_moderation.cli.menu:main",
        ],
    },
)