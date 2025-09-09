- [Custom Python Component](#custom-python-component)
  - [Purpose](#purpose)
    - [Comparison to Python Transformations](#comparison-to-python-transformations)
    - [Key features](#key-features)
  - [Configuration](#configuration)
    - [Git configuration](#git-configuration)
    - [SSH configuration](#ssh-configuration)
    - [Example: Running code saved in custom repository + template 🧩](#example-running-code-saved-in-custom-repository--template-)
    - [Example: Listing preinstalled packages](#example-listing-preinstalled-packages)
    - [Example: Accessing custom configuration parameters](#example-accessing-custom-configuration-parameters)
  - [Code examples – Keboola Common Interface guidance](#code-examples--keboola-common-interface-guidance)
    - [Loading configuration parameters](#loading-configuration-parameters)
    - [Working with data types](#working-with-data-types)
    - [Creating a table with predefined schema](#creating-a-table-with-predefined-schema)
    - [Writing a table with dynamic schema](#writing-a-table-with-dynamic-schema)
    - [Accessing input tables from mapping](#accessing-input-tables-from-mapping)
  - [Processing input files](#processing-input-files)
    - [Grouping files by tags](#grouping-files-by-tags)
    - [Creating output files](#creating-output-files)
  - [Processing state files](#processing-state-files)
    - [Handling errors](#handling-errors)
  - [Logging](#logging)
  - [Development](#development)
  - [Integration](#integration)


# Custom Python Component

This component allows you to run custom Python code directly within Keboola. It supports secure user parameters provided
via the Keboola UI configuration.

## Purpose

The primary purpose of this component is to enable the rapid creation of custom integrations (connectors) that can be
configured and executed directly in Keboola. This eliminates the need to build and maintain a separate custom component.

### Comparison to Python Transformations

- **Use Cases**:
    - **[Python Transformations](https://help.keboola.com/transformations/python-plain/)**: Designed exclusively for data transformation within Keboola. These work with data
      already present in Keboola storage and save processed results back into storage.
    - **Custom Python Component**: Ideal for creating integrations or applications that interact with external systems,
      download or push data, or require user-provided secure parameters (e.g., API keys, passwords).

> Note: Avoid using Python Transformations for integrations with external systems requiring secure parameters.

### Key features

- **Secure Parameters**: Safely provide encrypted parameters (e.g., API keys, passwords) via the Keboola UI
  configuration using the `#` prefix.
- **Customizable Environment**:
    - Clean container image to install only required Python packages.
    - Support for multiple Python versions.
- **Flexible Code Execution**: Run code from:
    - A public or private Git repository.
    - Directly within the Keboola UI configuration.


## Configuration

- `source`: Source of the code to run.
  - `code`: Custom code entered in a text field (default).
  - `git`: Custom repository.
- `user_properties`: Object containing custom configuration parameters. The key names prefixed with `#` will be encrypted upon saving.
- `venv`: String with one of the following values:
  - `3.12`, `3.13` (default), `3.14` – Run your code in an isolated environment containing just the packages of your choice and the respective Python version.
  - `base` – Run your code in a shared environment (contains many pre-installed packages in legacy versions)
- `git`: Object containing configuration of the git repository, which shall be cloned and run (`"source": "git"` only).
- `code`: JSON encoded Python code to run (`"source": "code"` only).
- `packages`: Array of extra packages to be installed (`"source": "code"` only). *If you're not sure whether you need to install certain package or not, you can run the command `uv pip list` via subprocess (see the example below).*


### Git configuration

The git configuration object supports the following parameters:

- `url`: Repository URL – supports both HTTPS and SSH formats.
- `branch`: Branch name to checkout – UI provides branch selection.
- `filename`: Python script filename to execute – UI lists available files.
- `auth`: Repository visibility & authentication method.
  - `none`: Public repository, no authentication (default).
  - `pat`: Private repository, Personal Access Token.
  - `ssh`: Private repository, SSH key.
- `#token`: Personal Access Token (`"auth": "pat"` only). This value will be encrypted in Keboola Storage.
- `ssh_keys`: SSH keys configuration object (`"auth": "ssh"` only).


### SSH configuration

- `keys`: Object containing both public and private keys.
  - `public`: Public key saved in your Git project. This value is not passed by the component and is saved just for future reference.
  - `#private`: Private key used for authentication. This value will be encrypted in Keboola Storage.


### Example: Running code saved in custom repository + template 🧩

As this might become a preferred way of running custom Python code in Keboola for many, we prepared a [simple example project](https://github.com/keboola/component-custom-python-example-repo-1), which help you with your first steps (and can also server you as a template for any of your future projects).


Contents of the `config.json` file:

```json
{
  "parameters": {
    "source": "git",
    "venv": "3.13",
    "git": {
      "url": "https://github.com/keboola/component-custom-python-example-repo-1.git",
      "branch": "main",
      "filename": "main.py",
      "auth": "none",
    },
    "user_properties": {
      "debug": true
    }
  }
}
```



### Example: Listing preinstalled packages

```py
import datetime
import subprocess

print("Hello world!")
print("Current date and time:", datetime.datetime.now())
print("See the full list of preinstalled packages:")

subprocess.check_call(["uv", "pip", "list"])
```

The above code in the `config.json` file format for local testing:

```json
{
  "parameters": {
    "source": "code",
    "venv": "base",
    "code": "import datetime\nimport subprocess\n\nprint(\"Hello world!\")\nprint(\"Current date and time:\", datetime.datetime.now())\nprint(\"See the full list of preinstalled packages:\")\n\nsubprocess.check_call([\"uv\", \"pip\", \"list\"])\n",
    "packages": []
  }
}
```


### Example: Accessing custom configuration parameters

*Note: The code to access user parameters is pre-populated in every new configuration.*

```py
from keboola.component import CommonInterface

ci = CommonInterface()
# access user parameters
print(ci.configuration.parameters)
```

The above code in the `config.json` file format for local testing:

```json
{
  "parameters": {
    "source": "code",
    "venv": "3.13",
    "code": "from keboola.component import CommonInterface\n\nci = CommonInterface()\n# access user parameters\nprint(ci.configuration.parameters)",
    "packages": [],
    "user_properties": {
      "debug": false
      "#secretCredentials": "theStrongestPasswordEver"
    }
  }
}
```

## Code examples – Keboola Common Interface guidance

These are code examples, recommendations and core principles that you should use when writing your custom code. It ensures that your code will work properly in the Keboola environment.

### Loading configuration parameters

```py
# Logger is automatically set up based on the component setup (GELF or STDOUT)
import logging

from keboola.component import CommonInterface

SOME_PARAMETER = "some_user_parameter"
REQUIRED_PARAMETERS = [SOME_PARAMETER]

# init the interface
# A ValueError error is raised if the KBC_DATADIR does not exist or contains non-existent path.
ci = CommonInterface()

# A ValueError error is raised if the config.json file does not exists in the data dir.
# Checks for required parameters and throws ValueError if any is missing.
ci.validate_configuration_parameters(REQUIRED_PARAMETERS)

# print KBC Project ID from the environment variable if present:
logging.info(ci.environment_variables.project_id)

# load particular configuration parameter
logging.info(ci.configuration.parameters[SOME_PARAMETER])
```

### Working with data types

For column data types always use BaseType definitions:
```py
# Base Type column examples
integer_col = ColumnDefinition(BaseType.integer(default=0))
timestamp_col = ColumnDefinition(BaseType.timestamp())
date_col = ColumnDefinition(BaseType.date())
numeric_col = ColumnDefinition(BaseType.numeric(length="38,2"))
string_col = ColumnDefinition(BaseType.string())
float_col = ColumnDefinition(BaseType.float())
```

### Creating a table with predefined schema

```py
import csv

from keboola.component import CommonInterface
from keboola.component.dao import BaseType, ColumnDefinition

# init the interface
ci = CommonInterface()

# get user parameters
parameters = ci.configuration.parameters

api_token = parameters["#api_token"]

# Define complete schema upfront (note that it is also possible to define the schema later,
# it just has to be defined before the manifest is written)
schema = {
    "id": ColumnDefinition(
        data_types=BaseType.integer(),
        primary_key=True,  # This column is the primary key, multiple columns can be defined as primary keys
    ),
    "created_at": ColumnDefinition(data_types=BaseType.timestamp()),
    "status": ColumnDefinition(),  # Default type is string
    "value": ColumnDefinition(data_types=BaseType.numeric(length="38,2")),
}

# Create table definition with predefined schema
out_table = ci.create_out_table_definition(
    name="results.csv",  # File name for the output
    destination="out.c-data.results",  # Destination table in Keboola Storage
    schema=schema,  # Predefined schema (you can omit this if you want to define the schema later)
    incremental=True,  # Enable incremental loading (primary key must be defined in schema)
    has_header=True,  # Indicates that the CSV has a header row (True by default, can be defined later)
)

# Write some data to the output file
with open(out_table.full_path, "w+", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=out_table.column_names)
    writer.writeheader()
    writer.writerow({"id": "1", "created_at": "2023-01-15T14:30:00Z", "status": "completed", "value": "123.45"})

# Write manifest file so that Keboola knows about the output table schema
ci.write_manifest(out_table)
```

### Writing a table with dynamic schema

It may happen that it is not known upfront what is the schema of the result data. In this case, you can use `keboola.csvwriter`package that can dynamically adjust the schema as the data comes. The schema of the existing output table in Keboola must always be a subset of what you're trying to write, so you need to store the existing table schema in the state.

```py
from keboola.component import CommonInterface
from keboola.csvwriter import ElasticDictWriter

# init the interface
ci = CommonInterface()
# data with different headers
data = [
    {"id": "1", "created_at": "2023-01-15T14:30:00Z", "value": "123.45"},
    {"id": "2", "created_at": "2023-01-15T14:30:00Z", "new_value": "completed", "value": "123.45"},
]

# Create table definition with predefined schema
out_table = ci.create_out_table_definition(
    name="results_dynamic.csv",  # File name for the output
    destination="out.c-data.results",  # Destination table in Keboola Storage
    incremental=True,  # Enable incremental loading (primary key must be defined in schema)
    has_header=True,  # Indicates that the CSV has a header row (True by default, can be defined later)
)

# get previous columns from state file
last_state = ci.get_state_file() or {}
columns = last_state.get("table_column_names", {}).get(out_table.destination, [])

writer = ElasticDictWriter(
    out_table.full_path,
    fieldnames=columns,  # initial column name set
)
# Write some data to the output file
writer.writerows(data)

writer.writeheader()  # this is important as it includes the header in the data, otherwise the first row is treated as data

writer.close()
final_column_names = writer.fieldnames  # collect final column names from the writer after it's closed


# Update the output table definition with the final column names
out_table.schema = final_column_names  # all columns will be string
out_table.primary_key = ["id"]  # we know that the id from the provided columns is a primary key

# Update the state file with the final column names
state_file = {"table_column_names": {out_table.destination: final_column_names}}
# Write manifest file so that Keboola knows about the output table schema
ci.write_manifest(out_table)
# Write the state file
ci.write_state_file(state_file)
```



### Accessing input tables from mapping

```py
import csv

from keboola.component import CommonInterface

# Initialize the component
ci = CommonInterface()

# Access input mapping configuration
input_tables = ci.configuration.tables_input_mapping

# Process each input table
for table in input_tables:
    # Get the destination (filename in the /data/in/tables directory)
    table_name = table.destination

    # Load table definition from manifest
    table_def = ci.get_input_table_definition_by_name(table_name)

    # Print information about the table
    print(f"Processing table: {table_name}")
    print(f"  - Source: {table.source}")
    print(f"  - Full path: {table_def.full_path}")
    print(f"  - Columns: {table_def.column_names}")

    # Read data from the CSV file
    with open(table_def.full_path, "r") as input_file:
        csv_reader = csv.DictReader(input_file)
        for row in csv_reader:
            # Process each row
            print(f"  - Row: {row}")
```

## Processing input files

Similarly as tables, files and their manifest files are represented by the `keboola.component.dao.FileDefinition` object
and may be loaded using the convenience method `get_input_files_definitions()`. The result object contains all metadata
about the file, such as manifest file representations, system path and name.

The `get_input_files_definitions()` supports filter parameters to filter only files with a specific tag or retrieve only
the latest file of each. This is especially useful because the KBC input mapping will by default include all versions of
files matching specific tag. By default, the method returns only the latest file of each.

```py
import logging

from keboola.component import CommonInterface

# Initialize the interface
ci = CommonInterface()

# Get input files with specific tags (only latest versions)
input_files = ci.get_input_files_definitions(tags=["images", "documents"], only_latest_files=True)

# Process each file
for file in input_files:
    print(f"Processing file: {file.name}")
    print(f"  - Full path: {file.full_path}")
    print(f"  - Tags: {file.tags}")

    # Example: Process image files
    if "images" in file.tags:
        # Process image using appropriate library
        print(f"  - Processing image: {file.name}")
        # image = Image.open(file.full_path)
        # ... process image ...

    # Example: Process document files
    if "documents" in file.tags:
        print(f"  - Processing document: {file.name}")
        # ... process document ...
```

### Grouping files by tags

When working with files it may be useful to retrieve them in a dictionary structure grouped by tag:

```py
from keboola.component import CommonInterface

# Initialize the interface
ci = CommonInterface()

# Group files by tag
files_by_tag = ci.get_input_file_definitions_grouped_by_tag_group(only_latest_files=True)

# Process files for each tag
for tag, files in files_by_tag.items():
    print(f"Processing tag group: {tag}")
    for file in files:
        print(f"  - File: {file.name}")
        # Process file based on its tag
```

### Creating output files

Similar to tables, you can create output files with appropriate manifests:

```py
import json

from keboola.component import CommonInterface

# Initialize the interface
ci = CommonInterface()

# Create output file definition
output_file = ci.create_out_file_definition(
    name="results.json",
    tags=["processed", "results"],
    is_public=False,
    is_permanent=True,
)

# Write content to the file
with open(output_file.full_path, "w") as f:
    json.dump({"status": "success", "processed_records": 42}, f)

# Write manifest file
ci.write_manifest(output_file)
```

## Processing state files

[State files](https://developers.keboola.com/extend/common-interface/config-file/#state-file) allow your component to store and retrieve information between runs. This is especially useful for incremental processing or tracking the last processed data.

```py
from datetime import datetime

from keboola.component import CommonInterface

# Initialize the interface
ci = CommonInterface()

# Load state from previous run
state = ci.get_state_file()

# Get the last processed timestamp (or use default if this is the first run)
last_updated = state.get("last_updated", "1970-01-01T00:00:00Z")
print(f"Last processed data up to: {last_updated}")

# Process data (only data newer than last_updated)
# In a real component, this would involve your business logic
processed_items = [
    {"id": 1, "timestamp": "2023-05-15T10:30:00Z"},
    {"id": 2, "timestamp": "2023-05-16T14:45:00Z"},
]

# Get the latest timestamp for the next run
if processed_items:
    # Sort items by timestamp to find the latest one
    processed_items.sort(key=lambda x: x["timestamp"])
    new_last_updated = processed_items[-1]["timestamp"]
else:
    # No new items, keep the previous timestamp
    new_last_updated = last_updated

# Store the new state for the next run
ci.write_state_file(
    {
        "last_updated": new_last_updated,
        "processed_count": len(processed_items),
        "last_run": datetime.now().isoformat(),
    }
)

print(f"State updated, next run will process data from: {new_last_updated}")
```

State files can contain any serializable JSON structure, so you can store complex information:

```py
# More complex state example
state = {
    "last_run": datetime.now().isoformat(),
    "api_pagination": {
        "next_page_token": "abc123xyz",
        "page_size": 100,
        "total_pages_retrieved": 5,
    },
    "processed_ids": [1001, 1002, 1003, 1004],
    "statistics": {
        "success_count": 1000,
        "error_count": 5,
        "skipped_count": 10,
    },
}

ci.write_state_file(state)
```

### Handling errors

```py
try:
    # my code
    do_something()
except UserException as exc:
    logging.exception(
        exc,
        extra={"additional_detail": "xxx"},  # additional detail
    )
    exit(1)  # 1 is user exception
except Exception as exc:
    logging.exception(
        exc,
        extra={"additional_detail": "xxx"},  # additional detail
    )
    exit(2)  # 2 is an unhandled application error
```
## Logging

Always use `logging` library as it's using our rich logger after CommonInterface initialisation.

```py
import logging

from keboola.component import CommonInterface

# init the interface
ci = CommonInterface()

logging.info("Info message")
logging.warning("Warning message")
logging.exception(exception, extra={"additional_detail": "xxx"}) # log errors
```



## Development

If needed, update the local data folder path by replacing the `CUSTOM_FOLDER` placeholder in the `docker-compose.yml` file:

```yaml
    volumes:
      - ./:/code
      - ./CUSTOM_FOLDER:/data
```

Clone the repository, initialize the workspace, and run the component using the following commands:

```sh
git clone git@github.com:keboola/component-custom-python.git
cd component-custom-python
docker compose build
docker compose up dev
```

To run the test suite and perform a lint check, use:

```sh
docker compose up test
```


## Integration

For details on deployment and integration with Keboola, refer to the
[deployment section of the developer
documentation](https://developers.keboola.com/extend/component/deployment/).
