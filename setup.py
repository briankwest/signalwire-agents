#!/usr/bin/env python3
from setuptools import setup, find_packages
import os

# Read the content of requirements.txt
with open('requirements.txt') as f:
    required = f.read().splitlines()

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
    data_files=[
        ('', ['schema.json']),  # Install schema.json in the root of the package
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
