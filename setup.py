from setuptools import setup

setup(
    name="mfile",
    version="0.1.0",
    description="Python binding for libmagic library",
    author="Paweł Srokosz",
    author_email="psrok1@gmail.com",
    packages=["mfile"],
    license="MIT",
    zip_safe=False,
    package_data={
        'mfile': ['libmagic/*.dll', 'libmagic/*.dylib', 'libmagic/*.mgc', 'libmagic/*.so*', 'libmagic/*.la']
    },
    python_requires='>=3.6',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License'
    ]
)
