"""Sphinx configuration for python-sendparcel."""

import sys
from pathlib import Path

# Make the src/ package importable for autodoc.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

project = "python-sendparcel"
copyright = "2025, Dominik Kozaczko"
author = "Dominik Kozaczko"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "plans"]

html_theme = "furo"
html_static_path = ["_static"]

autodoc_member_order = "bysource"
autodoc_typehints = "description"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
