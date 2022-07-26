import os
import yaml
import pydantic
from typing import Optional, List, Dict
from pathlib import Path

from parm.api.match_result import MatchResult
from parm.api.exceptions import PatternMismatchException
from parm.programs.capstone import CapstoneProgram


class Signature(pydantic.BaseModel):
    name: Optional[str]
    imports: List[str] = []
    exports: List[str]
    method: str = 'find_single'
    pattern: str

    def __hash__(self):
        return id(self)


class SignatureResult(pydantic.BaseModel):
    name: Optional[str]
    result: str
    errors: List[str] = []
    matches: Dict[str, int] = {}


def signature_result_representer(dumper: yaml.Dumper, data: SignatureResult):
    result_dict = {}
    if data.name:
        result_dict['name'] = data.name
    result_dict['result'] = data.result
    if data.errors:
        result_dict['errors'] = data.errors
    if data.matches:
        result_dict['matches'] = data.matches
    return dumper.represent_data(result_dict)


class CustomDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


CustomDumper.add_representer(SignatureResult, signature_result_representer)


def parse_signature_document(doc):
    try:
        return Signature(**doc)
    except pydantic.ValidationError as e:
        print(e)
        raise e


def parse_signature_result_document(doc):
    try:
        return SignatureResult(**doc)
    except pydantic.ValidationError as e:
        print(e)
        raise e


def load_yaml_docs(path):
    if isinstance(path, str):
        path = Path(path)
    with path.open('r') as src:
        return list(yaml.safe_load_all(src))


def load_signature_file(path):
    documents = load_yaml_docs(path)
    return [parse_signature_document(doc) for doc in documents]


def load_signature_result_file(path):
    documents = load_yaml_docs(path)
    return [parse_signature_result_document(doc) for doc in documents]


class DependencyException(Exception):
    pass


class RecursiveDependencyException(DependencyException):
    pass


class NotRunnableDependencyException(DependencyException):
    pass


class FailedDependencyException(DependencyException):
    pass


class BadPassedDependencyException(DependencyException):
    pass


class MatchingCtx:
    def __init__(self, match_target):
        self.match_target = match_target

        self.signatures = []
        self.passed_signatures = []
        self.failed_signatures = []
        self.not_run_signatures = set()

        self.error_map = {}

        self.exporter_map = {}  # type: Dict[str, List[Signature]]
        self.importer_map = {}

        self.match_results = {}

    def add_signature(self, signature):
        self.signatures.append(signature)
        for exp in signature.exports:
            self.exporter_map.setdefault(exp, []).append(signature)
        for imp in signature.imports:
            self.importer_map.setdefault(imp, []).append(signature)

    def perform_match(self, signature):
        mr = MatchResult()
        for imp in signature.imports:
            mr[imp] = self.match_results[imp]
        method = getattr(self.match_target, signature.method)

        try:
            with mr.transact():
                method(signature.pattern, match_result=mr)
            self.passed_signatures.append(signature)
        except PatternMismatchException:
            self.failed_signatures.append(signature)

        for exp in signature.exports:
            try:
                result = mr[exp]
            except KeyError:
                self.add_signature_error(signature, f'symbol [{exp}] was not exported')
                continue
            try:
                old_result = self.match_results[exp]
            except KeyError:
                self.match_results[exp] = result
            else:
                assert old_result == result
                self.match_results[exp] = result

    def resolve(self, signature, active_set=None):
        if active_set is None:
            active_set = set()

        if signature in self.failed_signatures:
            raise FailedDependencyException()

        if signature in active_set:
            raise RecursiveDependencyException()

        if signature in self.not_run_signatures:
            raise NotRunnableDependencyException()

        if signature in self.passed_signatures:
            # If the signature had actually matched the required imports, we would never have gotten here...
            raise BadPassedDependencyException()

        active_set.add(signature)

        dont_run = False
        for imp in signature.imports:
            if imp in self.match_results:
                continue

            for exporter in self.exporter_map.get(imp, []):
                try:
                    self.resolve(exporter, active_set)
                    break
                except DependencyException:
                    continue
            else:
                self.mark_signature_not_run(signature, f'unresolved import [{imp}]')
                dont_run = True
        if dont_run:
            return

        self.perform_match(signature)

    def add_signature_error(self, signature, error):
        self.error_map.setdefault(signature, []).append(error)

    def mark_signature_not_run(self, signature, reason):
        self.not_run_signatures.add(signature)
        self.add_signature_error(signature, reason)


def _get_signature_result(signature, ctx: MatchingCtx):
    if signature in ctx.failed_signatures:
        return 'failure'
    elif signature in ctx.passed_signatures:
        return 'pass'
    else:
        assert signature in ctx.not_run_signatures
        return 'not run'


def create_signature_result(signature, ctx: MatchingCtx):
    matches = {}
    for exp in signature.exports:
        try:
            result = ctx.match_results[exp]
        except KeyError:
            continue
        matches[exp] = int(result)

    return SignatureResult(
        name=signature.name,
        result=_get_signature_result(signature, ctx),
        errors=ctx.error_map.get(signature, []),
        matches=matches
    )


class SignatureMatchingGroup:
    def __init__(self, signatures, match_result_path):
        self.signatures = signatures
        self.match_result_path = match_result_path

    def append_to_context(self, ctx):
        for sig in self.signatures:
            ctx.add_signature(sig)

    def save_matches(self, ctx):
        srs = []
        for sig in self.signatures:
            srs.append(create_signature_result(sig, ctx))
        with open(self.match_result_path, 'w') as dst:
            yaml.dump_all(srs, sort_keys=False, stream=dst, Dumper=CustomDumper)


def find_all_signature_files(path):
    assert os.path.exists(path)
    if os.path.isfile(path):
        return [path]
    assert os.path.isdir(path)
    result = []
    for root, dir_names, file_names in os.walk(path):
        for filename in file_names:
            if os.path.splitext(filename)[-1] != '.parm':
                continue
            result.append(os.path.join(root, filename))
    return result


def load_signature_matching_groups(match_map):
    groups = []
    for sig_file_path, output_path in match_map.items():
        signatures = load_signature_file(sig_file_path)
        groups.append(SignatureMatchingGroup(signatures, output_path))
    return groups


def _create_match_map(signatures_path, output_path):
    sig_file_paths = find_all_signature_files(signatures_path)
    assert sig_file_paths, 'No signatures found!'

    if output_path is None:
        output_path = signatures_path

    if not output_path.endswith('/') and not signatures_path.endswith('\\') and not os.path.isdir(output_path) and len(
            sig_file_paths) == 1:
        match_map = {signatures_path: output_path + '.match'}
    else:
        match_map = {}
        for path in sig_file_paths:
            assert path.startswith(signatures_path) and path.endswith('.parm')
            piece = path[len(signatures_path):] + '.match'
            match_map[path] = os.path.join(output_path, piece)

    return match_map


def match_signatures(target_path, match_map):
    assert isinstance(match_map, dict)

    target = CapstoneProgram.load_arm_elf(Path(target_path))
    groups = load_signature_matching_groups(match_map)
    match_ctx = MatchingCtx(target)

    for group in groups:
        group.append_to_context(match_ctx)
    for group in groups:
        for signature in group.signatures:
            match_ctx.resolve(signature)
        group.save_matches(match_ctx)


def match_signature_files(target_path, signatures_path, output_path=None):
    match_map = _create_match_map(signatures_path, output_path)
    match_signatures(target_path, match_map)


def load_signature_results(sig_results):
    sig_result_paths = []
    if isinstance(sig_results, str):
        sig_results = Path(sig_results)
    if isinstance(sig_results, Path):
        if sig_results.is_dir():
            for path in sig_results.rglob('*'):
                if path.name.endswith('.match'):
                    sig_result_paths.append(path)
        else:
            sig_result_paths = [sig_results]
    else:
        sig_result_paths = map(Path, sig_results)

    results = {}
    for p in sig_result_paths:
        for result in load_signature_result_file(p):
            assert result.name not in results
            results[result.name] = result
    return results
