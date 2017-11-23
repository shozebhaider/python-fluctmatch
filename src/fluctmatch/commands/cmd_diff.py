# -*- Mode: python; tab-width: 4; indent-tabs-mode:nil; coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
#
# fluctmatch --- https://github.com/tclick/python-fluctmatch
# Copyright (c) 2013-2017 The fluctmatch Development Team and contributors
# (see the file AUTHORS for the full list of names)
#
# Released under the New BSD license.
#
# Please cite your use of fluctmatch in published work:
#
# Timothy H. Click, Nixon Raj, and Jhih-Wei Chu.
# Calculation of Enzyme Fluctuograms from All-Atom Molecular Dynamics
# Simulation. Meth Enzymology. 578 (2016), 327-342,
# doi:10.1016/bs.mie.2016.05.024.
#
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os
from os import path

import click
from future.builtins import open
from future.utils import native_str

from fluctmatch.analysis import paramtable


@click.command(
    "diff",
    short_help="Calculate differences between two tables."
)
@click.option(
    "-o",
    "--outdir",
    metavar="OUTDIR",
    default=os.getcwd(),
    show_default=True,
    type=click.Path(
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    help="Directory",
)
@click.option(
    "-r",
    "--ressep",
    metavar="RESSEP",
    default=3,
    show_default=True,
    type=click.IntRange(0, None, clamp=True),
    help="Number of residues to exclude in I,I+r"
)
@click.argument(
    "table1",
    metavar="TABLE1",
    type=click.Path(
        exists=True,
        file_okay=True,
        resolve_path=True,
    ),
)
@click.argument(
    "table2",
    metavar="TABLE2",
    type=click.Path(
        exists=True,
        file_okay=True,
        resolve_path=True,
    ),
)
def cli(outdir, ressep, table1, table2):
    table_1 = paramtable.ParamTable(ressep=ressep)
    table_1.from_file(table1)

    table_2 = paramtable.ParamTable(ressep=ressep)
    table_2.from_file(table2)

    d_table = table_1 - table_2
    d_perres = table_1.per_residue.subtract(
        table_2.per_residue,
        fill_value=0.0
    )
    d_interactions = table_1.interactions.subtract(
        table_2.interactions,
        fill_value=0.0
    )

    filename = path.join(outdir, "dcoupling.txt")
    with open(filename, mode="wb") as output:
        click.echo("Writing table differences to {}".format(filename))
        d_table = d_table.to_csv(
            header=True,
            index=True,
            sep=native_str(" "),
            float_format=native_str("%.4f"),
            encoding="utf-8",
        )
        output.write(d_table.encode())

    filename = path.join(outdir, "dperres.txt")
    with open(filename, mode="wb") as output:
        print("Writing per residue differences to {}".format(filename))
        d_perres = d_perres.to_csv(
            header=True,
            index=True,
            sep=native_str(" "),
            float_format=native_str("%.4f"),
            encoding="utf-8",
        )
        output.write(d_perres.encode())

    filename = path.join(outdir, "dinteractions.txt")
    with open(filename, mode="wb") as output:
        click.echo("Writing residue-residue differences to {}".format(filename))
        d_interactions = d_interactions.to_csv(
            header=True,
            index=True,
            sep=native_str(" "),
            float_format=native_str("%.4f"),
            encoding="utf-8",
        )
        output.write(d_interactions.encode())