from setuptools import setup, find_packages

setup(
    name="voguescrapper",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "selenium",
        "webdriver_manager",
    ],
)
