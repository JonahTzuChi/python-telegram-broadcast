from setuptools import setup, find_packages

setup(
    name='python-telegram-broadcast',
    version='0.1',
    packages=find_packages(),
    description='Package that wraps the python-telegram-bot library to make broadcasting easier.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Jonah Whaler',
    author_email='jk_saga@proton.me',
    license='MIT',
    install_requires=[
        "python-telegram-bot==21.1.1",
        "mypy"
    ]
)
