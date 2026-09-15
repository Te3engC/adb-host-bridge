from setuptools import setup

setup(
    name="adb-host-bridge",
    version="0.1.0",
    packages=["adb_host_bridge"],
    entry_points={"console_scripts": [
        "hostadb=adb_host_bridge.cli:main",
        "hadb=adb_host_bridge.adb_proxy:main",
    ]},
    python_requires=">=3.9",
)
