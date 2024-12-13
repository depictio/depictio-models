# Depictio Models

`depictio-models` is a Python package that provides shared data models for use across the [depictio](https://github.com/depictio/depictio) [depictio-cli](https://github.com/depictio/depictio-cli) and other components of the Depictio ecosystem. It is built using [Pydantic](https://pydantic-docs.helpmanual.io/) for robust data validation and serialization.

## Features
- Centralized Pydantic models for reusability across Depictio tools.
- Ensures consistent validation and structure for shared data.
- Lightweight and easy to integrate.

## Installation

To install `depictio-models`, clone the repository and install it in editable mode:

```bash
# Clone the repository
git clone https://github.com/depictio/depictio-models.git
cd depictio-models

# Install in editable mode
pip install -e .
```

## Usage

After installation, you can import and use the models in your project. For example:

```python
from depictio_models.models.cli import CLIConfig

# Example usage
config = CLIConfig(api_base_url="http://localhost:8058", user={...})
print(config.dict())
```

## Development

To contribute or modify the models:

1. Clone the repository.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Make changes and ensure all tests pass before submitting a pull request.

### Running Tests

We use `pytest` for testing. To run the test suite:

```bash
pytest
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

For more information, visit the [Depictio GitHub page](https://github.com/depictio).

