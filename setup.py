import setuptools

with open("README.md", "r") as f:
    README = f.read()

setuptools.setup(
    name="pymsb",
    version="1.0.0",
    author="Aurum",
    url="https://github.com/SunakazeKun/pymsb",
    description="Python library for Nintendo's MSBT and MSBF formats",
    long_description=README,
    long_description_content_type="text/markdown",
    keywords=["nintendo", "lms", "msbt", "msbf", "modding"],
    packages=setuptools.find_packages(),
    python_requires=">=3.10",
    license="gpl-3.0",
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3 :: Only"
    ]
)
