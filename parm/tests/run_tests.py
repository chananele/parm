import pytest
import sys
import os


def main():
    os.chdir(os.path.dirname(__file__))
    pytest.main(['-x', '.'])


if __name__ == '__main__':
    sys.exit(main())
