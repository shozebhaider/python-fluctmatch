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
from future.builtins import open
from future.utils import native_str

import functools
import glob
import multiprocessing as mp
from os import path

import numpy as np
import pandas as pd
from fluctmatch.fluctmatch import charmmfluctmatch


def calculate_thermo(subdir, **kwargs):
    topology = path.join(subdir, kwargs.pop("topology",
                                            "fluctmatch.xplor.psf"))
    trajectory = path.join(subdir, kwargs.pop("trajectory", "cg.dcd"))
    window = path.basename(subdir)

    cfm = charmmfluctmatch.CharmmFluctMatch(
        topology, trajectory, outdir=subdir, **kwargs)
    cfm.calculate_thermo(nma_exec=kwargs.get("nma_exec"))

    with open(cfm.filenames["thermo_data"], "rb") as data_file:
        table = pd.read_csv(
            data_file,
            header=0,
            index_col=["segidI", "resI"],
            skipinitialspace=True,
            delim_whitespace=True)

    return (window, table)


def create_thermo_tables(datadir, outdir, **kwargs):
    """Create several thermodynamics tables from CHARMM calculations.

    Parameters
    ----------
    datadir : str
        Subdirectory of data
    outdir : str
        Directory to output tables
    topology : filename or Topology object
        A CHARMM/XPLOR PSF topology file, PDB file or Gromacs GRO file;
        used to define the list of atoms. If the file includes bond
        information, partial charges, atom masses, ... then these data will
        be available to MDAnalysis. A "structure" file (PSF, PDB or GRO, in
        the sense of a topology) is always required. Alternatively, an
        existing :class:`MDAnalysis.core.topology.Topology` instance may
        also be given.
    trajectory : filename
        A trajectory that has the same number of atoms as the topology.
    temperature : float, optional
        Temperature of system
    nma_exec : str, optional
        Path for CHARMM executable
    charmm_version : int, optional
        CHARMM version
    """
    subdirs = (_ for _ in glob.iglob(path.join(datadir, "*")) if path.isdir(_))

    calc_thermo = functools.partial(calculate_thermo, **kwargs)
    pool = mp.Pool(maxtasksperchild=2)
    results = pool.map_async(calc_thermo, subdirs)
    pool.close()
    pool.join()
    results.wait()

    entropy = pd.DataFrame()
    enthalpy = pd.DataFrame()
    heat = pd.DataFrame()

    for window, result in results.get():
        entropy = pd.concat(
            [entropy, pd.DataFrame(result["Entropy"], columns=window)], axis=1)
        entropy.columns = entropy.columns.astype(np.int)
        entropy = entropy[np.sort(entropy.columns)]

        enthalpy = pd.concat(
            [enthalpy,
             pd.DataFrame(result["Enthalpy"], columns=window)],
            axis=1)
        enthalpy.columns = enthalpy.columns.astype(np.int)
        enthalpy = enthalpy[np.sort(enthalpy.columns)]

        heat = pd.concat(
            [heat, pd.DataFrame(result["Heatcap"], columns=window)], axis=1)
        heat.columns = heat.columns.astype(np.int)
        heat = heat[np.sort(heat.columns)]

        temperature = kwargs.get("temperature", 300.)
        gibbs = enthalpy - (temperature * entropy)

        filename = path.join(outdir, "entropy.txt")
        with open(filename, mode="wb") as thermo:
            table = entropy.to_csv(
                header=True,
                index=True,
                sep=native_str(" "),
                float_format=native_str("%.4f"),
                encoding="utf-8",
            )
            thermo.write(table.encode())

        filename = path.join(outdir, "enthalpy.txt")
        with open(filename, mode="wb") as thermo:
            table = enthalpy.to_csv(
                header=True,
                index=True,
                sep=native_str(" "),
                float_format=native_str("%.4f"),
                encoding="utf-8",
            )
            thermo.write(table.encode())

        filename = path.join(outdir, "heat_capacity.txt")
        with open(filename, mode="wb") as thermo:
            table = heat.to_csv(
                header=True,
                index=True,
                sep=native_str(" "),
                float_format=native_str("%.4f"),
                encoding="utf-8",
            )
            thermo.write(table.encode())

        filename = path.join(outdir, "gibbs.txt")
        with open(filename, mode="wb") as thermo:
            table = gibbs.to_csv(
                header=True,
                index=True,
                sep=native_str(" "),
                float_format=native_str("%.4f"),
                encoding="utf-8",
            )
            thermo.write(table.encode())
