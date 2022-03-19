from setuptools import setup

setup(
    name='openpracticelibrary-tweetbot',
    version='0.0.1',
    packages=['openpracticelibrarytweetbot'],
    install_requires=[
        'pyyaml',
        'pylint',
        'urllib3'
    ],
    entry_points = {
        'console_scripts': ['oplscheduletweets = openpracticelibrarytweetbot.__main__:main'],
    }
)