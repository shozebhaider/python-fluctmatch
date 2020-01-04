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

import MDAnalysis as mda
import numpy as np
from numpy import testing

from fluctmatch.libs import fluctmatch as fmutils

from ..datafiles import TPR
from ..datafiles import XTC


def test_average_structure():
    universe: mda.Universe = mda.Universe(TPR, XTC)
    avg_positions: np.ndarray = np.mean(
        [universe.atoms.positions for _ in universe.trajectory], axis=0)
    positions: np.ndarray = fmutils.AverageStructure(
        universe.atoms).run().result
    testing.assert_allclose(
        positions,
        avg_positions,
        err_msg="Average coordinates don't match.",
    )


def test_bond_stats():
    universe: mda.Universe = mda.Universe(TPR, XTC)
    avg_bonds: np.ndarray = np.mean(
        [universe.bonds.bonds() for _ in universe.trajectory], axis=0)
    bond_fluct: np.ndarray = np.std(
        [universe.bonds.bonds() for _ in universe.trajectory], axis=0)
    bonds = fmutils.BondStats(universe.atoms).run().result
    testing.assert_allclose(
        bonds.average,
        avg_bonds,
        err_msg="Average bond distances don't match.",
    )
    testing.assert_allclose(
        bonds.stddev,
        bond_fluct,
        err_msg="Bond fluctuations don't match.",
    )
