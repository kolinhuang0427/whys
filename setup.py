from setuptools import setup, find_packages

setup(
    name="whys",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "whys=whys.cli:cli",
        ],
    },
    description="Annotate code with reasons. Get 'why' when you need it.",
    author="Kolin Huang",
    author_email="kolin@codey.ai",
    url="https://github.com/kolinhuang0427/whys",
    python_requires=">=3.8",
)