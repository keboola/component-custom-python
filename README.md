# Custom Python Component

This component lets you run your own Python code directly within Keboola, with support for custom dependencies configured via the UI.


## Configuration

- `code`: JSON encoded Python code to run.
- `packages`: List of extra packages to be installed.

If you're not sure whether you need to install certain package or not, you can run the command `uv pip list` via subprocess (see the example below).


### Example: Listing preinstalled packages

```py
import datetime
import subprocess

print("Hello world!")
print("Current date and time:", datetime.datetime.now())
print("See the full list of preinstalled packages:")

subprocess.check_call(["uv", "pip", "list"])
```

```json
{
    "parameters": {
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

```json
{
    "parameters": {
        "code": "from keboola.component import CommonInterface\n\nci = CommonInterface()\n# access user parameters\nprint(ci.configuration.parameters)",
        "packages": [],
        "user_properties": {
            "debug": false
            "#secretCredentials": "theStrongestPasswordEver"
        }
    }
}
```


## Development

If needed, update the local data folder path by replacing the `CUSTOM_FOLDER` placeholder in the `docker-compose.yml` file:

```
    volumes:
      - ./:/code
      - ./CUSTOM_FOLDER:/data
```

Clone the repository, initialize the workspace, and run the component using the following commands:

```
git clone git@github.com:keboola/component-custom-python.git
cd component-custom-python
docker compose build
docker compose up dev
```

To run the test suite and perform a lint check, use:

```
docker compose up test
```


## Integration

For details on deployment and integration with Keboola, refer to the
[deployment section of the developer
documentation](https://developers.keboola.com/extend/component/deployment/).
