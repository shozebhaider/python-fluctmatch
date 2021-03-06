# -*- Mode: python; tab-width: 4; indent-tabs-mode:nil; coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
#
# pysca --- https://github.com/tclick/python-pysca
# Copyright (c) 2015-2017 The pySCA Development Team and contributors
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
from future.builtins import (dict, open, zip)

import logging
import logging.config
import os
from os import path

import click
import pandas as pd
import MDAnalysis as mda


@click.command(
    "table_convert",
    short_help="Transform an ENM IC table name to corresponding atoms.")
@click.option(
    "-l",
    "--logfile",
    metavar="LOG",
    show_default=True,
    default=path.join(os.getcwd(), "table_convert.log"),
    type=click.Path(exists=False, file_okay=True, resolve_path=True),
    help="Log file",
)
@click.option(
    "-s1",
    "top1",
    metavar="FILE",
    default=path.join(os.getcwd(), "cg.xplor.psf"),
    show_default=True,
    type=click.Path(exists=True, file_okay=True, resolve_path=True),
    help="Topology file",
)
@click.option(
    "-s2",
    "top2",
    metavar="FILE",
    default=path.join(os.getcwd(), "fluctmatch.xplor.psf"),
    show_default=True,
    type=click.Path(exists=True, file_okay=True, resolve_path=True),
    help="Topology file",
)
@click.option(
    "-f",
    "coord",
    metavar="FILE",
    default=path.join(os.getcwd(), "cg.dcd"),
    show_default=True,
    type=click.Path(exists=True, file_okay=True, resolve_path=True),
    help="Coordinate file",
)
@click.option(
    "-t",
    "--table",
    metavar="FILE",
    default=path.join(os.getcwd(), "kb.txt"),
    show_default=True,
    type=click.Path(exists=True, file_okay=True, resolve_path=True),
    help="Coordinate file",
)
@click.option(
    "-o",
    "--outfile",
    metavar="OUTFILE",
    default=path.join(os.getcwd(), "kb_aa.txt"),
    show_default=True,
    type=click.Path(exists=False, file_okay=True, resolve_path=True),
    help="Table file",
)
def cli(logfile, top1, top2, coord, table, outfile):
    # Setup logger
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,  # this fixes the problem
        "formatters": {
            "standard": {
                "class": "logging.Formatter",
                "format": "%(name)-12s %(levelname)-8s %(message)s",
            },
            "detailed": {
                "class": "logging.Formatter",
                "format":
                "%(asctime)s %(name)-15s %(levelname)-8s %(message)s",
                "datefmt": "%m-%d-%y %H:%M",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
            },
            "file": {
                "class": "logging.FileHandler",
                "filename": path.join(os.getcwd(), logfile),
                "level": "INFO",
                "mode": "w",
                "formatter": "detailed",
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console", "file"]
        },
    })
    logger = logging.getLogger(__name__)

    cg = mda.Universe(top1, coord)
    fluctmatch = mda.Universe(top2, coord)
    convert = dict(zip(fluctmatch.atoms.names, cg.atoms.names))
    resnames = pd.DataFrame.from_records(
        zip(cg.residues.segids, cg.residues.resnums, cg.residues.resnames),
        columns=["segid", "res", "resn"]
    ).set_index(["segid", "res"])

    with open(table, "rb") as tbl:
        logger.info("Loading {}.".format(table))
        constants = pd.read_csv(
            tbl,
            header=0,
            skipinitialspace=True,
            delim_whitespace=True,
        )
        logger.info("Table loaded successfully.")

    # Transform assigned bead names to an all-atom designation.
    constants["I"] = constants["I"].apply(lambda x: convert[x])
    constants["J"] = constants["J"].apply(lambda x: convert[x])

    # Create lists of corresponding residues
    columns = ["segidI", "resI", "segidJ", "resJ"]
    resnI = []
    resnJ = []
    for segidI, resI, segidJ, resJ in constants[columns].values:
        resnI.append(resnames.loc[(segidI, resI),])
        resnJ.append(resnames.loc[(segidJ, resJ),])
    constants["resnI"] = pd.concat(resnI).values
    constants["resnJ"] = pd.concat(resnJ).values

    # Concatenate the columns
    cols = ["segidI", "resI", "resnI", "I", "segidJ", "resJ", "resnJ", "J"]
    constants.set_index(cols, inplace=True)

    with open(outfile, "wb") as output:
        logger.info("Writing updated table to {}.".format(outfile))
        constants = constants.to_csv(
            header=True,
            index=True,
            sep=" ",
            float_format="%.4f",
        )
        output.write(constants.encode())
        logger.info("Table written successfully.")
