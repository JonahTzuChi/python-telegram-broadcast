from setuptools import setup, find_packages

DESCRIPTION = 'Package that wraps the python-telegram-bot library to make broadcasting easier.'

setup(
    name='python-telegram-broadcast',
    version='0.4',
    packages=find_packages(),
    description=DESCRIPTION,
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='jonah_whaler_2348',
    author_email='jk_saga@proton.me',
    license='MIT',
    install_requires=[
        "python-telegram-bot==21.1.1",
        "mypy"
    ],
    keywords=[
        'python', 'telegram', 'broadcast', 'bot'
    ],
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
    ]
)
