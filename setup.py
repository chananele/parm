from setuptools import setup, find_packages


setup(
    name="parm",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'lark',
    ],
    entry_points={
        'console_scripts': [
            'test=parm.test:main',
        ]
    }
)
