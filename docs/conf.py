"""Sphinx configuration."""

import os
import sys

import django


project = "django-segments"
author = "Jack Linke"
copyright = "2024, Jack Linke"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_click",
    "myst_parser",
]
autodoc_typehints = "description"
html_theme = "furo"

# Add package path to sys.path
sys.path.insert(0, os.path.join(os.path.abspath('.'), '../'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'

# Initialize Django
django.setup()
