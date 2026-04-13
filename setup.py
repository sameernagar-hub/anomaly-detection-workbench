import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="anomaly-detection-workbench",
    version="1.0.0",
    author="Sameer Nagar",
    author_email="nagarsam8989@gmail.com",
    description="Drift-robust, argument-aware anomaly detection workbench with analysis, live monitoring, evaluation, and run archiving",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sameernagar-hub/anomaly-detection-workbench",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
