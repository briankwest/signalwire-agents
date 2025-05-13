#!/usr/bin/env python3
from setuptools import setup, find_packages
import os

# Read the content of requirements.txt
with open('requirements.txt') as f:
    required = f.read().splitlines()

# Copy schema.json to the package directory if it's not already there
schema_src = os.path.join(os.path.dirname(__file__), 'schema.json')
schema_dst = os.path.join(os.path.dirname(__file__), 'signalwire_agents', 'schema.json')
if os.path.exists(schema_src) and not os.path.exists(schema_dst):
    import shutil
    os.makedirs(os.path.dirname(schema_dst), exist_ok=True)
    shutil.copy2(schema_src, schema_dst)
    print(f"Copied schema.json to {schema_dst}")

setup(
    name="signalwire_agents",
    version="0.1.0",
    description="SignalWire AI Agents SDK",
    author="SignalWire Team",
    author_email="info@signalwire.com",
    url="https://github.com/signalwire/signalwire-ai-agents",
    packages=find_packages(),
    install_requires=required,
    python_requires=">=3.7",
    include_package_data=True,
    package_data={
        'signalwire_agents': ['schema.json'],
    },
    data_files=[
        ('', ['schema.json']),  # Also install schema.json in the root of the package
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
