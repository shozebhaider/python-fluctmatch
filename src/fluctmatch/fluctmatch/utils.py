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
from future.utils import PY2

import copy
import os
import subprocess
import tempfile
import textwrap
from os import path

import click
import MDAnalysis as mda
import MDAnalysis.analysis.base as analysis
import numpy as np
import pandas as pd
from MDAnalysis.coordinates import memory
from MDAnalysis.lib import util as mdutil
from future.builtins import (dict, super)
from future.utils import native_str

from fluctmatch.fluctmatch.data import charmm_split

if PY2:
    FileNotFoundError = OSError


class AverageStructure(analysis.AnalysisBase):
    """Calculate the average structure of a trajectory.
    """

    def __init__(self, atomgroup, **kwargs):
        """
        Parameters
        ----------
        atomgroup : :class:`~MDAnalysis.Universe.AtomGroup`
            An AtomGroup
        start : int, optional
            start frame of analysis
        stop : int, optional
            stop frame of analysis
        step : int, optional
            number of frames to skip between each analysed frame
        verbose : bool, optional
            Turn on verbosity
        """
        super().__init__(atomgroup.universe.trajectory, **kwargs)
        self._ag = atomgroup

    def _prepare(self):
        self.result = []

    def _single_frame(self):
        self.result.append(self._ag.positions)

    def _conclude(self):
        self.result = np.mean(self.result, axis=0)


class BondStats(analysis.AnalysisBase):
    """Calculate either the average bond length or the fluctuation in bond lengths.

    """

    def __init__(self, atomgroup, func="mean", **kwargs):
        """
        Parameters
        ----------
        atomgroup : :class:`~MDAnalysis.Universe.AtomGroup`
            An AtomGroup
        func : {"mean", "std", "both"}, optional
            Calculate either the mean or the standard deviation of the bonds
        start : int, optional
            start frame of analysis
        stop : int, optional
            stop frame of analysis
        step : int, optional
            number of frames to skip between each analysed frame
        verbose : bool, optional
            Turn on verbosity
        """
        super().__init__(atomgroup.universe.trajectory, **kwargs)
        self._ag = atomgroup
        if func == "mean":
            self._func = (np.mean, )
        elif func == "std":
            self._func = (np.std, )
        elif func == "both":
            self._func = (np.mean, np.std)
        else:
            raise AttributeError("func must either be 'mean' or 'std'")

    def _prepare(self):
        self.result = []

    def _single_frame(self):
        self.result.append(self._ag.bonds.bonds())

    def _conclude(self):
        self.result = [func(self.result, axis=0) for func in self._func]
        bonds = [
            pd.concat(
                [
                    pd.Series(self._ag.bonds.atom1.names),
                    pd.Series(self._ag.bonds.atom2.names),
                    pd.Series(_),
                ],
                axis=1) for _ in self.result
        ]
        for _ in bonds:
            _.columns = ["I", "J", "r_IJ"]
        self.result = copy.deepcopy(bonds)


def write_charmm_files(universe,
                       outdir=os.getcwd(),
                       prefix="cg",
                       write_traj=True,
                       **kwargs):
    """Write CHARMM coordinate, topology PSF, stream, and topology RTF files.

    Parameters
    ----------
    universe : :class:`~MDAnalysis.Universe` or :class:`~MDAnalysis.AtomGroup`
        A collection of atoms in a universe or AtomGroup with bond definitions.
    outdir : str
        Location to write the files.
    prefix : str
        Prefix of filenames
    write_traj : bool
        Write the trajectory to disk.
    charmm_version
        Version of CHARMM for formatting (default: 41)
    extended
        Use the extended format.
    cmap
        Include CMAP section.
    cheq
        Include charge equilibration.
    title
        Title lines at the beginning of the file.
    """
    from MDAnalysis.core import (
        topologyattrs, )

    # Attempt to create the necessary subdirectory
    try:
        os.makedirs(outdir)
    except OSError:
        pass

    filename = path.join(outdir, prefix)
    filenames = dict(
        psf_file=".".join((filename, "psf")),
        xplor_psf_file=".".join((filename, "xplor", "psf")),
        crd_file=".".join((filename, "cor")),
        stream_file=".".join((filename, "stream")),
        topology_file=".".join((filename, "rtf")),
        traj_file=".".join((filename, "dcd")),
    )

    # Write required CHARMM input files.
    print("Writing {}...".format(filenames["topology_file"]))
    with mda.Writer(native_str(filenames["topology_file"]), **kwargs) as rtf:
        rtf.write(universe)
    print("Writing {}...".format(filenames["stream_file"]))
    with mda.Writer(native_str(filenames["stream_file"]), **kwargs) as stream:
        stream.write(universe)
    print("Writing {}...".format(filenames["psf_file"]))
    with mda.Writer(native_str(filenames["psf_file"]), **kwargs) as psf:
        psf.write(universe)

    # Write the new trajectory in Gromacs XTC format.
    if write_traj:
        print("Writing the trajectory {}...".format(filenames["traj_file"]))
        print("This may take a while depending upon the size and "
              "length of the trajectory.")
        with mda.Writer(
                native_str(filenames["traj_file"]),
                universe.atoms.n_atoms,
                remarks="Written by fluctmatch.") as trj:
            universe.trajectory.rewind()
            with click.progressbar(universe.trajectory) as bar:
                for ts in bar:
                    trj.write(ts)

    # Write an XPLOR version of the PSF
    atomtypes = topologyattrs.Atomtypes(universe.atoms.names)
    universe._topology.add_TopologyAttr(topologyattr=atomtypes)
    universe._generate_from_topology()
    print("Writing {}...".format(filenames["xplor_psf_file"]))
    with mda.Writer(native_str(filenames["xplor_psf_file"]), **kwargs) as psf:
        psf.write(universe)

    # Calculate the average coordinates, average bond lengths, and
    # fluctuations of bond lengths from the trajectory.
    if universe.trajectory.n_frames > 1:
        print("Determining the average structure of the trajectory. ")
        print("Note: This could take a while depending upon the "
              "size of your trajectory.")
        positions = AverageStructure(universe.atoms).run()
        avg_universe = mda.Universe(
            filenames["psf_file"], [
                positions.result,
            ],
            format=memory.MemoryReader,
            order="fac")
        print("Writing {}...".format(filenames["crd_file"]))
        with mda.Writer(
                native_str(filenames["crd_file"]), dt=1.0, **kwargs) as crd:
            crd.write(avg_universe.atoms)
    else:
        print("Writing {}...".format(filenames["crd_file"]))
        with mda.Writer(
                native_str(filenames["crd_file"]), dt=1.0, **kwargs) as crd:
            crd.write(universe.atoms)


def split_gmx(info, data_dir=path.join(os.getcwd(), "data"), **kwargs):
    """Create a subtrajectory from a Gromacs trajectory.

    Parameters
    ----------
    info : :class:`collections.namedTuple`
        Contains information about the data subdirectory and start and
        stop frames
    data_dir : str, optional
        Location of the main data directory
    topology : str, optional
        Topology filename (e.g., tpr gro g96 pdb brk ent)
    trajectory : str, optional
        A Gromacs trajectory file (e.g., xtc trr)
    index : str, optional
        A Gromacs index file (e.g., ndx)
    outfile : str, optional
        A Gromacs trajectory file (e.g., xtc trr)
    logfile : str, optional
        Log file for output of command
    system : int
        Atom selection from Gromacs index file (0 = System, 1 = Protein)
    """
    if mdutil.which("gmx") is None:
        raise OSError("Gromacs 5.0+ is required. "
                      "If installed, please ensure that it is in your path.")

    # Trajectory splitting information
    subdir, start, stop = info
    subdir = path.join(data_dir, "{}".format(subdir))

    # Attempt to create the necessary subdirectory
    try:
        os.makedirs(subdir)
    except OSError:
        pass

    # Various filenames
    topology = kwargs.get("topology", "md.tpr")
    trajectory = kwargs.get("trajectory", path.join(os.curdir, "md.xtc"))
    index = kwargs.get("index")
    outfile = kwargs.get("outfile", "aa.xtc")
    logfile = kwargs.get("logfile", "split.log")

    if index is not None:
        command = [
            "gmx",
            "-s",
            topology,
            "-f",
            trajectory,
            "-n",
            index,
            "-o",
            path.join(subdir, outfile),
            "-b",
            "{:d}".format(start),
            "-e",
            "{:d}".format(stop),
        ]
    else:
        command = [
            "gmx",
            "trjconv",
            "-s",
            topology,
            "-f",
            trajectory,
            "-o",
            path.join(subdir, outfile),
            "-b",
            "{:d}".format(start),
            "-e",
            "{:d}".format(stop),
        ]
    fd, fpath = tempfile.mkstemp(text=True)
    with mdutil.openany(fpath, "w") as temp:
        print(kwargs.get("system", 0), file=temp)
    with mdutil.openany(fpath, "r") as temp, \
        mdutil.openany(path.join(subdir, logfile), mode="w") as log:
        subprocess.check_call(
            command, stdin=temp, stdout=log, stderr=subprocess.STDOUT)
    os.remove(fpath)


def split_charmm(info, data_dir=path.join(os.getcwd(), "data"), **kwargs):
    """Create a subtrajectory from a CHARMM trajectory.

    Parameters
    ----------
    info : :class:`collections.namedTuple`
        Contains information about the data subdirectory and start and
        stop frames
    data_dir : str, optional
        Location of the main data directory
    toppar : str, optional
        Directory containing CHARMM topology/parameter files
    trajectory : str, optional
        A CHARMM trajectory file (e.g., dcd)
    outfile : str, optional
        A CHARMM trajectory file (e.g., dcd)
    logfile : str, optional
        Log file for output of command
    charmm_version : int
        Version of CHARMM
    """
    if mdutil.which("charmm") is None:
        raise OSError("CHARMM is required. If installed, "
                      "please ensure that it is in your path.")

    # Trajectory splitting information
    subdir, start, stop = info
    subdir = path.join(data_dir, "{}".format(subdir))

    # Attempt to create the necessary subdirectory
    try:
        os.makedirs(subdir)
    except OSError:
        pass

    # Various filenames
    version = kwargs.get("charmm_version", 41)
    toppar = kwargs.get("toppar",
                        "/opt/local/charmm/c{:d}b1/toppar".format(version))
    trajectory = kwargs.get("trajectory", path.join(os.curdir, "md.dcd"))
    outfile = path.join(subdir, kwargs.get("outfile", "aa.dcd"))
    logfile = kwargs.get("logfile", "split.log")
    inpfile = path.join(subdir, "split.inp")

    with mdutil.openany(inpfile, "w") as charmm_input:
        charmm_inp = charmm_split.split_inp.format(
            toppar=toppar,
            trajectory=trajectory,
            outfile=outfile,
            version=version,
            start=start,
            stop=stop,
        )
        charmm_inp = textwrap.dedent(charmm_inp[1:])
        print(charmm_inp, file=charmm_input)
    command = [
        "charmm",
        "-i",
        inpfile,
        "-o",
        path.join(subdir, logfile),
    ]
    subprocess.check_call(command)
