# ------------------------------------------------------------------------------
#   python-fluctmatch
#   Copyright (c) 2013-2020 Timothy H. Click, Ph.D.
#
#   All rights reserved.
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#
#   Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
#   Neither the name of the author nor the names of its contributors may be used
#   to endorse or promote products derived from this software without specific
#   prior written permission.
#
#    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
#    AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#    IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#    ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
#    ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
#    DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#    SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#    CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
#    LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
#    OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
#    DAMAGE.
#
#   Timothy H. Click, Nixon Raj, and Jhih-Wei Chu.
#   Simulation. Meth Enzymology. 578 (2016), 327-342,
#   Calculation of Enzyme Fluctuograms from All-Atom Molecular Dynamics
#   doi:10.1016/bs.mie.2016.05.024.
#
# ------------------------------------------------------------------------------

import functools
import logging
import logging.config
import multiprocessing as mp
import os
from os import path

import click
from MDAnalysis.lib import util as mdutil

from ..libs import fluctmatch

_CONVERT = dict(GMX=fluctmatch.split_gmx, CHARMM=fluctmatch.split_charmm)


@click.command("splittraj", short_help="Split a trajectory using Gromacs or CHARMM.")
@click.option(
    "--type",
    "program",
    type=click.Choice(_CONVERT.keys()),
    default="GMX",
    help="Split using an external MD program",
)
@click.option(
    "-s",
    "topology",
    metavar="FILE",
    default=path.join(os.getcwd(), "md.tpr"),
    type=click.Path(exists=False, file_okay=True, resolve_path=True),
    help="Gromacs topology file (e.g., tpr gro g96 pdb brk ent)",
)
@click.option(
    "--toppar",
    metavar="DIR",
    default=path.join(os.getcwd(), "toppar"),
    type=click.Path(exists=False, file_okay=False, resolve_path=True),
    help="Location of CHARMM topology/parameter files",
)
@click.option(
    "-f",
    "trajectory",
    metavar="FILE",
    default=path.join(os.getcwd(), "md.xtc"),
    type=click.Path(exists=False, file_okay=True, resolve_path=True),
    help="Trajectory file (e.g. xtc trr dcd)",
)
@click.option(
    "--data",
    metavar="DIR",
    default=path.join(os.getcwd(), "data"),
    type=click.Path(
        exists=False, file_okay=False, writable=True, readable=True, resolve_path=True,
    ),
    help="Directory to write data.",
)
@click.option(
    "-n",
    "index",
    metavar="FILE",
    type=click.Path(exists=False, file_okay=True, resolve_path=True),
    help="Gromacs index file (e.g. ndx)",
)
@click.option(
    "-o",
    "outfile",
    metavar="FILE",
    default="aa.xtc",
    type=click.Path(exists=False, file_okay=True, resolve_path=False),
    help="Trajectory file (e.g. xtc trr dcd)",
)
@click.option(
    "-l",
    "--logfile",
    metavar="LOG",
    show_default=True,
    default="splittraj.log",
    type=click.Path(exists=False, file_okay=True, resolve_path=False),
    help="Log file",
)
@click.option(
    "-t",
    "--system",
    metavar="NDXNUM",
    default=0,
    show_default=True,
    type=click.IntRange(0, None, clamp=True),
    help="System selection based upon Gromacs index file",
)
@click.option(
    "-b",
    "start",
    metavar="FRAME",
    default=1,
    show_default=True,
    type=click.IntRange(1, None, clamp=True),
    help="Start time of trajectory",
)
@click.option(
    "-e",
    "stop",
    metavar="FRAME",
    default=10000,
    show_default=True,
    type=click.IntRange(1, None, clamp=True),
    help="Stop time of total trajectory",
)
@click.option(
    "-w",
    "window_size",
    metavar="WINSIZE",
    default=10000,
    show_default=True,
    type=click.IntRange(2, None, clamp=True),
    help="Size of each subtrajectory",
)
def cli(
    program,
    toppar,
    topology,
    trajectory,
    data,
    index,
    outfile,
    logfile,
    system,
    start,
    stop,
    window_size,
):
    logging.config.dictConfig(
        dict(
            version=1,
            disable_existing_loggers=False,  # this fixes the problem
            formatters=dict(
                standard={
                    "class": "logging.Formatter",
                    "format": "%(name)-12s %(levelname)-8s %(message)s",
                },
                detailed={
                    "class": "logging.Formatter",
                    "format": (
                        "%(asctime)s %(name)-15s %(levelname)-8s " "%(message)s"
                    ),
                    "datefmt": "%m-%d-%y %H:%M",
                },
            ),
            handlers=dict(
                console={
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "standard",
                },
                file={
                    "class": "logging.FileHandler",
                    "filename": logfile,
                    "level": "INFO",
                    "mode": "w",
                    "formatter": "detailed",
                },
            ),
            root=dict(level="INFO", handlers=["console", "file"]),
        )
    )
    logger: logging.Logger = logging.getLogger(__name__)

    if program == "GMX" and mdutil.which("gmx") is None:
        msg = (
            "Gromacs 5.0+ is required. If installed, please ensure that it "
            "is in your path."
        )
        logger.error(msg=msg)
        raise OSError(msg)
    if program == "CHARMM" and mdutil.which("charmm") is None:
        msg = (
            "CHARMM is required. If installed, please ensure that it is in "
            "your path."
        )
        logger.error(msg=msg)
        raise OSError(msg)

    half_size = window_size // 2
    beg = start - half_size if start >= window_size else start
    values = zip(
        range(beg, stop + 1, half_size),
        range(beg + window_size - 1, stop + 1, half_size),
    )
    values = [((y // half_size) - 1, x, y) for x, y in values]

    func = functools.partial(
        _CONVERT[program],
        data_dir=data,
        topology=topology,
        toppar=toppar,
        trajectory=trajectory,
        index=index,
        outfile=outfile,
        logfile=logfile,
        system=system,
    )

    # Run multiple instances simultaneously
    pool = mp.Pool()
    pool.map_async(func, values)
    pool.close()
    pool.join()
