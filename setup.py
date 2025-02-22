from setuptools import setup, find_packages


# Load the version from the shared VERSION file
def read_version():
    with open("VERSION", "r") as version_file:
        return version_file.read().strip()


setup(
    name="depictio-models",
    version=read_version(),
    description="Shared models for depictio-cli and depictio deployment",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Thomas Weber",
    author_email="thomas.weber@embl.de",
    url="https://github.com/depictio/depictio-models",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pydantic",
        "bleach",
        "bson",
        "colorlog",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
