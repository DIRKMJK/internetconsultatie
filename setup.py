import pathlib
from setuptools import setup

HERE = pathlib.Path(__file__).parent
README = (HERE / "readme.md").read_text()


setup(name='internetconsultatie',
    version='0.0.1',
    description='Download metadata and individual responses of Dutch government online consultations',
    long_description=README,
    long_description_content_type="text/markdown",
    author='dirkmjk',
    author_email='info@dirkmjk.nl',
    url='https://github.com/DIRKMJK/internetconsultatie',
    license="MIT",
    packages=['internetconsultatie'],
    install_requires=[
        'requests', 'pandas', 'bs4', 'nltk', 'textract', 'networkx'
    ],
    zip_safe=False)
