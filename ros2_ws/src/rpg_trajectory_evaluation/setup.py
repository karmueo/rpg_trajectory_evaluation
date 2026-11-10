from setuptools import find_packages, setup

package_name = 'rpg_trajectory_evaluation'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=[
        'numpy>=1.24',
        'matplotlib>=3.6',
        'colorama>=0.4',
        'PyYAML>=6',
    ],
    python_requires='>=3.10',
    zip_safe=True,
    maintainer='Zichao Zhang',
    maintainer_email='zzhang@ifi.uzh.ch',
    description='Evaluation toolbox for visual(-inertial) odometry and '
                'SLAM trajectories.',
    license='MIT',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'analyze_trajectory_single = '
            'rpg_trajectory_evaluation.cli.analyze_trajectory_single:main',
            'analyze_trajectories = '
            'rpg_trajectory_evaluation.cli.analyze_trajectories:main',
            'change_eval_cfg_recursive = '
            'rpg_trajectory_evaluation.cli.change_eval_cfg_recursive:main',
            'recursive_clean_results_dir = '
            'rpg_trajectory_evaluation.cli.recursive_clean_results_dir:main',
            'asl_groundtruth_to_pose = '
            'rpg_trajectory_evaluation.cli.dataset_tools.'
            'asl_groundtruth_to_pose:main',
            'bag_to_pose = '
            'rpg_trajectory_evaluation.cli.dataset_tools.bag_to_pose:main',
            'stamp_state_est = '
            'rpg_trajectory_evaluation.cli.dataset_tools.'
            'stamp_state_est:main',
            'stamp_state_est_using_matches = '
            'rpg_trajectory_evaluation.cli.dataset_tools.'
            'stamp_state_est_using_matches:main',
            'strip_gt_id = '
            'rpg_trajectory_evaluation.cli.dataset_tools.strip_gt_id:main',
            'transform_trajectory = '
            'rpg_trajectory_evaluation.cli.dataset_tools.'
            'transform_trajectory:main',
        ],
    },
)
