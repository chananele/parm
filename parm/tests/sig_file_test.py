import os
import unittest
import tempfile
import contextlib

from parm.signature_files import match_signature_files
from parm.tests.snippets import get_snippet_path
from parm.tests.sig_files import get_sig_path, get_expected_sig_result_path


@contextlib.contextmanager
def temp_file_path(suffix=None):
    fobj = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    fname = fobj.name
    fobj.close()
    try:
        yield fname
    finally:
        os.remove(fname)


def match_test_sig(target_path, sig_file_path, expected_output_path):
    with temp_file_path(suffix='.match') as dst:
        match_signature_files(target_path, sig_file_path, dst)
        with open(dst, 'r') as src:
            result = src.read()
    with open(expected_output_path, 'r') as src:
        expected = src.read()
    assert result == expected


# noinspection PyMethodMayBeStatic
class SigFileTest(unittest.TestCase):
    def match_snippet_sig(self, snippet_name, sig_name):
        match_test_sig(get_snippet_path(snippet_name), get_sig_path(sig_name), get_expected_sig_result_path(sig_name))

    def test_sanity(self):
        self.match_snippet_sig('mul', 'test1')
