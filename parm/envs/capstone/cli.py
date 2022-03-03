import sys
from pathlib import Path

import click

SUPPORTED_BUILDS = {
    ("arm", "32"),
}


@click.group(name="capstone")
@click.option("--arch", "-a", type=str, required=True, help="CPU-Architecture")
@click.option("--mode",
              "-m",
              type=str,
              required=True,
              help="Processor mode (64\\32\\16 bit)")
@click.option("--output",
              "-O",
              type=click.File('w'),
              default=sys.stdout,
              help="Output file (stdout by default)")
def cli(arch, mode, output):
    if (arch, mode) not in SUPPORTED_BUILDS:
        click.echo(
            f"Got ({arch}, {mode}) while currently only supporting: {SUPPORTED_BUILDS}",
            err=True)


@cli.command()
@click.argument("binary_path",
                type=click.Path(exists=True,
                                dir_okay=False,
                                resolve_path=True,
                                path_type=Path),
                required=True)
@click.option("--offset",
              "-o",
              type=int,
              default=0,
              help="Offset in binary to disassemble from")
@click.option("--size",
              type=int,
              default=None,
              help="size limit to disassemble, there is no limit by default")
def dump(binary_path: Path, offset: int, size: int):
    """
    Dump disassembly of a given binary file
    """
    # TODO: disassemble binary file to asm
    pass


@cli.group()
@click.argument("binary_path", type=click.Path(exists=True), required=True)
@click.option("--offset",
              "-o",
              type=int,
              default=0,
              help="Offset of first instruction")
@click.option("--size",
              type=int,
              default=None,
              help="size limit to disassemble, there is no limit by default")
@click.option("--pattern",
              "-p",
              type=click.Path(exists=True),
              default=None,
              help="path to pattern file\\folder of patterns")
def match(binary_path: Path, size: int, offset: int, patterns: Path):
    """
    Match a binary\\asm file against given patterns
    """
    # TODO: Disassemble binary file to asm
    # TODO: Load a given binary file into a CapstoneProgram
    # TODO: Define pattern file format
    # TODO: Read given patterns and feed into parm parsers
    pass


@match.command()
def findall():
    """
    Search for all given patterns in the given input
    """
    click.echo(
        f"TODO: Search for all signatures in the given asm {ctx['asm']}")
    click.echo('Not implemented yet', err=True)
    raise NotImplementedError()


@match.command()
@click.argument('symbols_to_find', type=str, nargs=-1)
def find(symbols_to_find):
    """
    Search for specific pattern from the given patterns in the given input
    """
    click.echo(
        f"TODO: Search specifically for {symbols_to_find} in the given asm {ctx['asm']}"
    )
    click.echo('Not implemented yet', err=True)
    raise NotImplementedError()
