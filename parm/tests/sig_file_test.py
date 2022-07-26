import os
import unittest
import tempfile
import contextlib

from parm.signature_files import match_signatures, load_signature_results
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


def match_test_sig(target_path, sig_file_path):
    with temp_file_path(suffix='.match') as dst:
        match_signatures(target_path, {sig_file_path: dst})
        return load_signature_results(dst)


def verify_test_sig(target_path, sig_file_path, expected_output_path):
    with temp_file_path(suffix='.match') as dst:
        match_signatures(target_path, {sig_file_path: dst})
        with open(dst, 'r') as src:
            result = src.read()
    with open(expected_output_path, 'r') as src:
        expected = src.read()
    assert result == expected


# noinspection PyMethodMayBeStatic
class SigFileTest(unittest.TestCase):
    def verify_snippet_sig(self, snippet_name, sig_name):
        verify_test_sig(get_snippet_path(snippet_name), get_sig_path(sig_name), get_expected_sig_result_path(sig_name))

    def match_snippet_sig(self, snippet_name, sig_name):
        return match_test_sig(get_snippet_path(snippet_name), get_sig_path(sig_name))

    def test_basic_sanity(self):
        self.verify_snippet_sig('mul', 'basic_sanity')

    def test_missing_import(self):
        self.verify_snippet_sig('mul', 'missing_dependency')

    def test_multiple_missing_imports(self):
        self.verify_snippet_sig('mul', 'multiple_missing_dependencies')

    def test_missing_export(self):
        self.verify_snippet_sig('mul', 'missing_export')

    def test_good_multi_sig(self):
        self.verify_snippet_sig('mul', 'good_multi_sig')

    def test_bad_multi_sig(self):
        self.verify_snippet_sig('mul', 'bad_multi_sig')

    def test_sig_result_sanity(self):
        results = self.match_snippet_sig('mul', 'basic_sanity')
        assert len(results) == 1
        result = results['basic_sanity']
        assert result.matches['test'] == 0x10458
