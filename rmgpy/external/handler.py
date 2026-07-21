#!/usr/bin/env python3

###############################################################################
#                                                                             #
# RMG - Reaction Mechanism Generator                                          #
#                                                                             #
# Copyright (c) 2002-2026 Prof. William H. Green (whgreen@mit.edu),           #
# Prof. Richard H. West (r.west@neu.edu) and the RMG Team (rmg_dev@mit.edu)   #
#                                                                             #
# Permission is hereby granted, free of charge, to any person obtaining a     #
# copy of this software and associated documentation files (the 'Software'),  #
# to deal in the Software without restriction, including without limitation   #
# the rights to use, copy, modify, merge, publish, distribute, sublicense,    #
# and/or sell copies of the Software, and to permit persons to whom the       #
# Software is furnished to do so, subject to the following conditions:        #
#                                                                             #
# The above copyright notice and this permission notice shall be included in  #
# all copies or substantial portions of the Software.                         #
#                                                                             #
# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR  #
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,    #
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE #
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER      #
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING     #
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER         #
# DEALINGS IN THE SOFTWARE.                                                   #
#                                                                             #
###############################################################################

import importlib.util
import json
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class ExternalEstimatorHandler:
    def __init__(self, path: str, kwargs: dict[str, Any] | None = None):
        self.path = Path(path).resolve()
        self.kwargs = kwargs or {}

        self._load_metadata()
        self._load_module()

    def _load_metadata(self):
        metadata_path = self.path / "metadata.json"
        if not metadata_path.exists():
            raise RuntimeError(f"Missing metadata.json in {self.path}")

        with metadata_path.open("r") as f:
            try:
                metadata = json.load(f)
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Could not parse metadata.json at {metadata_path}: {e}") from e

        self.name: str = metadata["name"]
        self.properties_estimated: list[str] = metadata["properties_estimated"]

        assert isinstance(self.name, str), f"name must be a string, got type {type(self.name)}"
        assert isinstance(self.properties_estimated, list), f"properties_estimated must be a string, got type {type(self.properties_estimated)}"

    def _load_module(self):
        estimate_py = self.path / "estimate.py"
        if not estimate_py.exists():
            raise RuntimeError(f"Missing estimate.py in {self.path}")

        spec = importlib.util.spec_from_file_location("", estimate_py)
        if spec is None or spec.loader is None:
            raise RuntimeError(
                f"importlib could not create a loader for {estimate_py}. "
                "Check that the file is a valid .py file."
            )

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        missing = [fn for fn in ("load", "estimate") if not hasattr(module, fn)]
        if missing:
            raise RuntimeError(
                f"{self.name}: estimate.py is missing required function(s): "
                + ", ".join(missing)
            )

        self.estimator = module.load(str(self.path), self.kwargs)
        self._estimate_fn = module.estimate

    def make_estimate(self, species, property_name: str) -> tuple[Any | None, str]:
        try:
            result = self._estimate_fn(species, self.estimator, property_name)
        except Exception as e:
            return None, (
                f"{self.name} raised an exception estimating '{property_name}' for {species.label}: {e}"
            )

        estimate, reason = result
        return estimate, reason