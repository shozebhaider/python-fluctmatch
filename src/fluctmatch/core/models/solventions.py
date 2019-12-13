#  python-fluctmatch -
#  Copyright (c) 2019 Timothy H. Click, Ph.D.
#
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#
#  Redistributions of source code must retain the above copyright notice, this
#  list of conditions and the following disclaimer.
#
#  Redistributions in binary form must reproduce the above copyright notice,
#  this list of conditions and the following disclaimer in the documentation
#  and/or other materials provided with the distribution.
#
#  Neither the name of the author nor the names of its contributors may be used
#  to endorse or promote products derived from this software without specific
#  prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
#  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#  ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
#  ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
#  DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#  SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#  OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#  Timothy H. Click, Nixon Raj, and Jhih-Wei Chu.
#  Calculation of Enzyme Fluctuograms from All-Atom Molecular Dynamics
#  Simulation. Meth Enzymology. 578 (2016), 327-342,
#  doi:10.1016/bs.mie.2016.05.024.
"""Class defining solvent ions."""

from typing import ClassVar
from typing import List
from typing import MutableMapping
from typing import NoReturn

import numpy as np
from MDAnalysis.core.topologyattrs import Atomtypes
from MDAnalysis.core.topologyattrs import Bonds

from ..base import ModelBase


class Model(ModelBase):
    """Select ions within the solvent."""

    description: ClassVar[str] = "Common ions within solvent (Li K Na F Cl Br I)"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._guess: bool = False
        self._mapping["ION"]: str = "name LI LIT K NA F CL BR I"
        self._selection.update(self._mapping)

    def _add_atomtypes(self) -> NoReturn:
        resnames: np.ndarray = np.unique(self.universe.residues.resnames)
        restypes: MutableMapping[str, int] = {
            k: v for k, v in zip(resnames, np.arange(resnames.size) + 10)
        }

        atomtypes: List[int] = [
            restypes[residue.resname] for residue in self.universe.residues
        ]
        self.universe.add_TopologyAttr(Atomtypes(atomtypes))

    def _add_bonds(self) -> NoReturn:
        self.universe.add_TopologyAttr(Bonds([]))
