from setuptools import setup, find_packages


setup(
    name='iot_project',
    version='0.1',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    package_data={"iot_project"},
    setup_requires = ["setuptools-scm"],
    install_requires=[
        "pandas",
        "pymongo",
        "bokeh",
    ],
    
    author='Daniela Komenda, Livio Bürgisser, Noémie Käser',
    author_email='komendan@students.zhaw.ch, buergli1@students.zhaw.ch, kaeseno1@students.zhaw.ch',
    description='IoT-Project for IoT-Course at ZHAW - FS24',
)
