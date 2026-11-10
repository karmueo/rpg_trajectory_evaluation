import importlib

import pytest


MODULES = [
    'rpg_trajectory_evaluation',
    'rpg_trajectory_evaluation.align_trajectory',
    'rpg_trajectory_evaluation.align_utils',
    'rpg_trajectory_evaluation.associate_timestamps',
    'rpg_trajectory_evaluation.compute_trajectory_errors',
    'rpg_trajectory_evaluation.fn_constants',
    'rpg_trajectory_evaluation.metrics',
    'rpg_trajectory_evaluation.multiple_traj_errors',
    'rpg_trajectory_evaluation.plot_utils',
    'rpg_trajectory_evaluation.results_writer',
    'rpg_trajectory_evaluation.report_writer',
    'rpg_trajectory_evaluation.trajectory',
    'rpg_trajectory_evaluation.trajectory_discovery',
    'rpg_trajectory_evaluation.trajectory_loading',
    'rpg_trajectory_evaluation.trajectory_utils',
    'rpg_trajectory_evaluation.transformations',
    'rpg_trajectory_evaluation.cli.analyze_trajectory_single',
    'rpg_trajectory_evaluation.cli.analyze_trajectories',
    'rpg_trajectory_evaluation.cli.change_eval_cfg_recursive',
    'rpg_trajectory_evaluation.cli.recursive_clean_results_dir',
    'rpg_trajectory_evaluation.cli.dataset_tools.asl_groundtruth_to_pose',
    'rpg_trajectory_evaluation.cli.dataset_tools.bag_to_pose',
    'rpg_trajectory_evaluation.cli.dataset_tools.stamp_state_est',
    'rpg_trajectory_evaluation.cli.dataset_tools.'
    'stamp_state_est_using_matches',
    'rpg_trajectory_evaluation.cli.dataset_tools.strip_gt_id',
    'rpg_trajectory_evaluation.cli.dataset_tools.transform_trajectory',
]

ENTRY_POINT_MODULES = [
    'rpg_trajectory_evaluation.cli.analyze_trajectory_single',
    'rpg_trajectory_evaluation.cli.analyze_trajectories',
    'rpg_trajectory_evaluation.cli.change_eval_cfg_recursive',
    'rpg_trajectory_evaluation.cli.recursive_clean_results_dir',
    'rpg_trajectory_evaluation.cli.dataset_tools.asl_groundtruth_to_pose',
    'rpg_trajectory_evaluation.cli.dataset_tools.bag_to_pose',
    'rpg_trajectory_evaluation.cli.dataset_tools.stamp_state_est',
    'rpg_trajectory_evaluation.cli.dataset_tools.'
    'stamp_state_est_using_matches',
    'rpg_trajectory_evaluation.cli.dataset_tools.strip_gt_id',
    'rpg_trajectory_evaluation.cli.dataset_tools.transform_trajectory',
]


@pytest.mark.parametrize('module_name', MODULES)
def test_module_imports(module_name):
    importlib.import_module(module_name)


@pytest.mark.parametrize('module_name', ENTRY_POINT_MODULES)
def test_entry_point_main_is_callable(module_name):
    module = importlib.import_module(module_name)
    assert callable(module.main)


def test_trajectory_is_exported():
    from rpg_trajectory_evaluation import Trajectory

    assert Trajectory.__name__ == 'Trajectory'
