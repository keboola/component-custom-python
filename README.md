Custom Python Application
=============


**Table of contents:**

[TOC]

Functionality Notes
===================

Prerequisites
=============

- Obtain the API token
- Register the application
- Any other necessary setup steps

Features
========

| **Feature**             | **Note**                                      |
|-------------------------|-----------------------------------------------|
| Generic UI form         | Provides a dynamic UI form.                               |
| Row-based configuration | Enables structured configuration using rows. |
| OAuth                   | OAuth authentication is enabled.                  |
| Incremental loading     | Supporst fetching data in increments.       |
| Backfill mode           | Allows seamless backfill setup.          |
| Date range filter       | Enables filtering data by a specifid date range.                           |

Supported Endpoints
===================

If you need additional endpoints, please submit a request to
[ideas.keboola.com](https://ideas.keboola.com/).

Configuration
=============

Param 1
-------

Param 2
-------

Output
======

- List of tables
- Foreign keys
- Schema

Development
-----------

If needed, update the local data folder path by replacing the `CUSTOM_FOLDER` placeholder in the `docker-compose.yml` file:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    volumes:
      - ./:/code
      - ./CUSTOM_FOLDER:/data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clone the repository, initialize the workspace, and run the component using the following commands:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
git clone git@bitbucket.org:kds_consulting_team/kds-team.app-custom-python.git kds-team.app-custom-python
cd kds-team.app-custom-python
docker-compose build
docker-compose run --rm dev
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To run the test suite and perform a lint check, use:

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
docker-compose run --rm test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Integration
===========

For details on deployment and integration with Keboola, refer to the
[deployment section of the developer
documentation](https://developers.keboola.com/extend/component/deployment/).
