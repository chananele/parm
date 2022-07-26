from setuptools import setup, find_packages


setup(
    name="parm",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'typing',
        'lark',
        'chainmap',
        'pytest',
        'pyelftools',
        'capstone',
        'construct',
        'pyyaml',
        'pydantic',
    ],
    entry_points={
        'console_scripts': [
            'parm-match-sigs=parm.signature_files.cli:main',
            'parm_cli=parm.tests.cli:main',
        ]
    }
)
