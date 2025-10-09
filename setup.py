# encoding: utf-8
from setuptools import setup, find_packages

#python setup.py sdist upload
setup(
    name='AIcon',
    version='0.1.0',
    author='Ildefons Magrans de Abril',
    author_email='ildefons.magrans@gmail.com',
    description='A simulator based developement framework of distributed management agents for the computing continuum.',
    long_description='\n\n'.join(
        open(f, 'rb').read().decode('utf-8')
        for f in ['README.md', 'CHANGELOG.md', 'AUTHORS.txt']),
    url='https://github.com/ildefons/aicon',
    license='modified MIT-style license with a non-commercial restriction',
    #packages=find_packages(where='src',exclude=("*.tests",)),
    packages=find_packages(where='src',exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
    package_dir={'': 'src'},
    include_package_data=True,

    install_requires=['simpy','pandas','networkx','numpy','tqdm'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Scientific/Engineering',
    ],
)
