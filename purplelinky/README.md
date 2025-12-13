# bluelinky (Python)

This repository now contains a Python port of the unofficial Hyundai/Kia Bluelink client. The API surface mirrors the previous TypeScript library while exposing Python classes that manage session handling and vehicle commands.

## Install

```sh
pip install .
```

## Example

```python
from bluelinky import BlueLinky, Region
from bluelinky.interfaces import BlueLinkyConfig

config = BlueLinkyConfig(
    username="someguy@example.com",
    password="hunter1",
    brand="hyundai",
    region=Region.US,
    pin="1234",
)

client = BlueLinky(config)
vehicle = client.get_vehicle("5NMS55555555555555")
if vehicle:
    response = vehicle.lock()
    print(response)
```

## Development

The Python package is managed with `pyproject.toml`. Install dependencies with `pip install -e .` to get an editable environment. The code currently includes a fully ported U.S. controller and placeholder implementations for other regions; contributions to flesh out the remaining regions are welcome.

## Warnings

Using Bluelinky may result in draining your 12V battery when refreshing from the car too often. Make sure you have read and understood the terms of use of your Kia or Hyundai account before using Bluelinky.
