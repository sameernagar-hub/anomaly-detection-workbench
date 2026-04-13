import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="anomaly-detection-workbench",
    version="0.0.2",
    author="Thijs van Ede",
    author_email="t.s.vanede@utwente.nl",
    description="Sequence-based anomaly detection workbench for system-log experiments",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/example/anomaly-detection-workbench",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
