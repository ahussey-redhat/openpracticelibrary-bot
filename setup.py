from setuptools import setup

setup(
    name='openpracticelibrary-bot',
    version='0.0.1',
    packages=['openpracticelibrarybot'],
    install_requires=[
        'pyyaml',
        'pylint',
        'urllib3'
    ],
    entry_points = {
        'console_scripts': ['oplbot = openpracticelibrarybot.__main__:run'],
    }
)