from setuptools import setup,find_packages
from pathlib import Path
readme=Path(__file__).parent/"README.md"
long_desc=readme.read_text(encoding="utf-8")if readme.exists()else""
setup(
    name="asmr18",
    version="0.0.3",
    author="Yosefario Dev",
    description="Downloader for ASMR18.fans",
    long_description=long_desc,
    long_description_content_type="text/markdown",
    url="https://github.com/yosefario-dev/asmr18",
    packages=find_packages(where="src"),
    package_dir={"":"src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "click>=8.1.0",
        "tqdm>=4.66.0",
        "colorama>=0.4.6",
        "pyyaml>=6.0",
    ],
    entry_points={"console_scripts":["asmr18=asmr18.cli:main"]},
    include_package_data=True,
    zip_safe=False,
)
