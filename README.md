# django-segments

[![PyPI](https://img.shields.io/pypi/v/django-segments.svg)][pypi status]
[![Status](https://img.shields.io/pypi/status/django-segments.svg)][pypi status]
[![Python Version](https://img.shields.io/pypi/pyversions/django-segments)][pypi status]
[![License](https://img.shields.io/pypi/l/django-segments)][license]

[![Read the documentation at https://django-segments.readthedocs.io/](https://img.shields.io/readthedocs/django-segments/latest.svg?label=Read%20the%20Docs)][read the docs]
[![Tests](https://github.com/OmenApps/django-segments/actions/workflows/tests.yml/badge.svg)][tests]
[![Codecov](https://codecov.io/gh/OmenApps/django-segments/branch/main/graph/badge.svg)][codecov]

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)][pre-commit]
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)][black]

[pypi status]: https://pypi.org/project/django-segments/
[read the docs]: https://django-segments.readthedocs.io/
[tests]: https://github.com/OmenApps/django-segments/actions?workflow=Tests
[codecov]: https://app.codecov.io/gh/OmenApps/django-segments
[pre-commit]: https://github.com/pre-commit/pre-commit
[black]: https://github.com/psf/black

## Overview

_Django Segments_ is a Django app that provides a way to create nested ranges of ranges. In this package we provide abstract models for `Spans`, which contain a set of `Segments`. Elsewhere, this concept is sometimes refered to as a "range list" or "range set".

*Note: Postgres has a [multirange](https://www.postgresql.org/docs/current/rangetypes.html) type, but there is no way to treat the ranges within a multirange as objects in their own right. This package provides a way to do that.*

The `Span` model is essentially a wrapper around a range field, and each `Span` contains one or more non-overlapping `Segment` model instances (which are also wrappers around range fields). The `Span` model is used to represent an entire range, and the `Segment` model instances each represent a non-overlapping portion of that range.

There are other ways to accomplish these general goals, but this package provides a more structured way to work with ranges of ranges, and a number of helper methods that make it easier to create, manipulate, and view Spans and Segments.

## Use Cases

This package is particularly useful for resourse scheduling and allocation, and can be used for a variety of other tasks.

### Resource Scheduling and Allocation

*This example is how the package will be used in a production application.*

Imagine you are building a system that allows an Irrigation District's water users to request water deliveries. You could use a `Span` to represent the period of time that a user has requested water, and `Segments` to represent the portions of that time that the user has actually received water, with a new segment created each time the volumetric flow rate changes.

### Work Order Tracking

Imagine you are building a system that tracks work orders for a manufacturing plant or trouble tickets for a helpdesk. You could use a `Span` to represent the span of time for each work order or ticket, and `Segments` to represent the portions of time the work order or ticket was spent in a particular state (e.g.: "In Progress", "On Hold", "Completed").

### Log File Analysis

Imagine you are building a system that analyzes log files. You could use a `Span` to represent each log file, and `Segments` to represent the portions of the log file that contain specific types of events.

### Conference Scheduling

Imagine you are building the schedule for a conference that runs from 8 am to 5 pm each day. You have a set of rooms, each of which can be scheduled for a specific time period. You could use a `Span` to represent the entire day for each room, and `Segments` to represent the time periods that each room is scheduled. The tools provided by this package would allow you to easily create, update (insert, delete, split, merge), and query the schedule for each room.

## Features

- Abstract models for building Spans and associated Segments
- Helper classes that can be used with multiple model variants (e.g.: two different models inheriting Span could use the same helper classes, use helper classes with overridden methods, or mix and match) and to aid in implementing forms and views.
- Extensive Tests
- Documentation
- Custom Django signals that allow the user to perform actions before and after each Operation is performed on a Span or Segment

## Requirements

- TODO

## Installation

You can install _django-segments_ via [pip] from [PyPI]:

```console
$ pip install django_segments
```

## Usage

Please see the [Usage Section] for details.

## Contributing

Contributions are very welcome.
To learn more, see the [Contributor Guide].

## License

Distributed under the terms of the [MIT license][license],
_django-segments_ is free and open source software.

## Issues

If you encounter any problems,
please [file an issue] along with a detailed description.

## Credits

This project was generated from [@OmenApps]'s [Cookiecutter Django Package] template.

[@omenapps]: https://github.com/OmenApps
[pypi]: https://pypi.org/
[cookiecutter django package]: https://github.com/OmenApps/cookiecutter-django-package
[file an issue]: https://github.com/OmenApps/django-segments/issues
[pip]: https://pip.pypa.io/

<!-- github-only -->

[license]: https://github.com/OmenApps/django-segments/blob/main/LICENSE
[contributor guide]: https://github.com/OmenApps/django-segments/blob/main/CONTRIBUTING.md
[usage section]: https://django-segments.readthedocs.io/en/latest/usage.html
