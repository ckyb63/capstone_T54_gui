from setuptools import setup
import os
from glob import glob

package_name = 'ppe_vending_gui'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name), glob('launch/*launch.[pxy][yma]*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Max Chen',
    maintainer_email='your.email@example.com',
    description='PPE Vending Machine GUI',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'gui_node = ppe_vending_gui.GUIros:main',
        ],
    },
) 