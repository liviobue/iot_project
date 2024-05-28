from setuptools import setup, find_packages


setup(
    name='iot_project',
    version='0.1',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    setup_requires = ["setuptools-scm"],
    install_requires=[
        "pymongo",
        "anyio",
        "RPi.GPIO",
        "smbus2",
        "numpy",
        "trio",
        "dotenv",
        "websockets",
        "picarx",
    ],
    extras_require={
        "notebook": [
            "bokeh",
        ],
    },
    author='Daniela Komenda, Livio Bürgisser, Noémie Käser',
    author_email='komendan@students.zhaw.ch, buergli1@students.zhaw.ch, kaeseno1@students.zhaw.ch',
    description='IoT-Project for IoT-Course at ZHAW - FS24',
)
