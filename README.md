- [Custom Python Component](#custom-python-component)
  - [Configuration](#configuration)
    - [Git configuration](#git-configuration)
    - [SSH configuration](#ssh-configuration)
    - [Example: Running code saved in custom repository](#example-running-code-saved-in-custom-repository)
    - [Example: Listing preinstalled packages](#example-listing-preinstalled-packages)
    - [Example: Accessing custom configuration parameters](#example-accessing-custom-configuration-parameters)
  - [Development](#development)
  - [Integration](#integration)


# Custom Python Component

This component lets you run your own Python code directly within Keboola, with support for custom dependencies configured via the UI.


## Configuration

- `source`: Source of the code to run.
  - `code`: Custom code entered in a text field (default).
  - `git`: Custom repository.
- `user_properties`: Object containing custom configuration parameters. The key names prefixed with `#` will be encrypted upon saving.
- `git`: Object containing configuration of the git repository, which shall be cloned and run (`"source": "git"` only).
- `code`: JSON encoded Python code to run (`"source": "code"` only).
- `packages`: Array of extra packages to be installed (`"source": "code"` only). *If you're not sure whether you need to install certain package or not, you can run the command `uv pip list` via subprocess (see the example below).*


### Git configuration

The git configuration object supports the following parameters:

- `url`: Repository URL – supports both HTTPS and SSH formats
- `branch`: Branch name to checkout – UI provides branch selection
- `filename`: Python script filename to execute – UI lists available files
- `auth`: Authentication method
  - `none`: Public repository, no authentication (default)
  - `pat`: Private repository using Personal Access Token
  - `ssh`: Private repository using SSH key
- `#token`: Personal Access Token (`"auth": "pat"` only). This value will be encrypted in Keboola Storage.
- `ssh_keys`: SSH keys configuration object (`"auth": "ssh"` only).


### SSH configuration

- `keys`: Object containing both public and private keys.
  - `public`: Public key saved in your Git project. This value is not passed by the component and is saved just for future reference.
  - `#private`: Private key used for authentication. This value will be encrypted in Keboola Storage.


### Example: Running code saved in custom repository

Contents of the `config.json` file:

```json
{
  "parameters": {
    "source": "git",
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
