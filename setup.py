from setuptools import setup, find_packages

setup(
    name="signalwire-agents",
    version="0.1.0",
    description="Python SDK for creating and hosting SignalWire AI Agents",
    author="SignalWire Team",
    author_email="info@signalwire.com",
    url="https://github.com/signalwire/signalwire-agents",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "pydantic>=1.9.0",
        "requests>=2.26.0",
        "pyyaml>=6.0",
        "python-dotenv>=0.19.1",
        "signalwire-pom>=0.1.0"
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)
