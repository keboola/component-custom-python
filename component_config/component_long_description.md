This component lets you run custom Python code directly within Keboola. Its main purpose is to enable fast creation of
custom integrations (connectors) that can be configured and executed inside Keboola—removing the need to build and
maintain a separate dedicated component.

### Comparison to Python Transformations

- **[Python Transformations](https://help.keboola.com/transformations/python-plain/)**: Focused purely on transforming
  data already in Keboola Storage, with results written back into storage.
- **Custom Python Component**: Suited for integrations or applications that interact with external systems, fetch or
  push data, or require secure parameters (e.g., API keys, passwords).

> **Note:** Do not use Python Transformations for external integrations requiring secure parameters.

### Key Features

- **Secure Parameters**: Provide sensitive values (API keys, tokens, passwords) safely via the Keboola UI using
  encrypted `#` parameters.
- **Customizable Environment**:
    - Clean container image to install only the dependencies you need.
    - Support for multiple Python versions.
- **Flexible Execution**: Run code from a public/private Git repository or directly within the Keboola UI configuration.  