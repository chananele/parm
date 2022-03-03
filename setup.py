from setuptools import setup, find_packages


setup(
    name="parm",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'lark',
        'chainmap',
        'pytest',
    ],
    entry_points={
        'console_scripts': [
            'parm_run_tests=parm.tests.run_tests:main',
            'parm_cli=parm.tests.cli:main',
            'iparm=parm.envs.ida.cli:cli',
            'cparm=parm.envs.capstone.cli:cli',
        ]
    }
)
