"""Sphinx configuration for Enthropy API documentation."""

project = "Enthropy"
copyright = "2026, Enthropy"
author = "Enthropy Engineering"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "furo"
html_static_path = ["_static"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
}

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}
