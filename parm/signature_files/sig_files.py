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


def parse_signature_document(doc):
    try:
        return Signature(**doc)
    except pydantic.ValidationError as e:
        print(e)
        raise e


def load_signature_file(path):
    with open(path, 'r') as src:
        documents = list(yaml.safe_load_all(src))
    return [parse_signature_document(doc) for doc in documents]


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
        self.not_run_signatures = []

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
            method(signature.pattern, match_result=mr)
            passed = True
            self.passed_signatures.append(signature)
        except PatternMismatchException:
            passed = False
            self.failed_signatures.append(signature)

        for exp in signature.exports:
            try:
                result = mr[exp]
            except KeyError:
                assert not passed
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

        for imp in signature.imports:
            if imp in self.match_results:
                continue

            for exporter in self.exporter_map[imp]:
                try:
                    self.resolve(exporter, active_set)
                    break
                except DependencyException:
                    continue
            else:
                self.not_run_signatures.append(signature)
                raise FailedDependencyException()

        self.perform_match(signature)


def format_signature_results(signature, ctx: MatchingCtx):
    lines = []
    if signature.name:
        lines.append(f'name: {signature.name}')

    if signature in ctx.failed_signatures:
        lines.append('result: failure')
        passed = False
    elif signature in ctx.passed_signatures:
        lines.append('result: pass')
        passed = True
    else:
        assert signature in ctx.not_run_signatures
        lines.append('result: not run')
        passed = False

    match_lines = []
    for exp in signature.exports:
        try:
            result = ctx.match_results[exp]
        except KeyError:
            assert not passed
            continue
        match_lines.append(f'  {exp}: {result}')

    if match_lines:
        lines.append('matches:')
        lines.extend(match_lines)

    return '---\n{}\n...\n\n'.format('\n'.join(lines))


class SignatureMatchingGroup:
    def __init__(self, signatures, match_result_path):
        self.signatures = signatures
        self.match_result_path = match_result_path

    def append_to_context(self, ctx):
        for sig in self.signatures:
            ctx.add_signature(sig)

    def save_matches(self, ctx):
        with open(self.match_result_path, 'w') as dst:
            for sig in self.signatures:
                print(format_signature_results(sig, ctx), file=dst)


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


def match_signature_files(target_path, signatures_path, output_path=None):
    sig_file_paths = find_all_signature_files(signatures_path)
    assert sig_file_paths, 'No signatures found!'

    if output_path is None:
        output_path = signatures_path

    if not output_path.endswith('/') and not signatures_path.endswith('\\') and not os.path.isdir(output_path) and len(
            sig_file_paths) == 1:
        match_map = {signatures_path: output_path}
    else:
        match_map = {}
        for path in sig_file_paths:
            assert path.startswith(signatures_path) and path.endswith('.parm')
            piece = path[len(signatures_path):] + '.match'
            match_map[path] = os.path.join(output_path, piece)

    target = CapstoneProgram.load_arm_elf(Path(target_path))
    groups = load_signature_matching_groups(match_map)
    match_ctx = MatchingCtx(target)

    for group in groups:
        group.append_to_context(match_ctx)
    for group in groups:
        for signature in group.signatures:
            match_ctx.resolve(signature)
        group.save_matches(match_ctx)
