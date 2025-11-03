"""
Setup configuration for Doodlify.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="doodlify",
    version="0.2.0",
    author="Doodlify Team",
    description="Automated Event-Based Frontend Customization Tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/doodlify",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "click>=8.1.0",
        "openai>=1.12.0",
        "GitPython>=3.1.40",
        "requests>=2.31.0",
        "pyyaml>=6.0.1",
        "mcp>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "doodlify=doodlify.cli:main",
        ],
    },
)
