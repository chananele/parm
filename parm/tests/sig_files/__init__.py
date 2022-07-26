import os


SIG_FILE_DIR = os.path.abspath(os.path.dirname(__file__))


def get_sig_path(name):
    return os.path.join(SIG_FILE_DIR, f'{name}.parm')


def get_expected_sig_result_path(name):
    return os.path.join(SIG_FILE_DIR, f'{name}.parm.expected')
