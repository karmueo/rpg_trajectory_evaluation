import math
import shutil

import yaml

from rpg_trajectory_evaluation import Trajectory
from rpg_trajectory_evaluation.cli.analyze_trajectory_single import main


def _load_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def _make_dataset(folder, synthetic_dataset):
    folder.mkdir(parents=True)
    shutil.copy2(synthetic_dataset / 'stamped_groundtruth.txt',
                 folder / 'stamped_groundtruth.txt')
    shutil.copy2(synthetic_dataset / 'stamped_traj_estimate.txt',
                 folder / 'stamped_traj_estimate.txt')
    shutil.copy2(synthetic_dataset / 'eval_cfg.yaml',
                 folder / 'eval_cfg.yaml')
    return folder


def _report_text(path):
    return path.read_text(encoding='utf-8')


def test_single_trajectory_cli_writes_statistics(synthetic_dataset):
    assert main([str(synthetic_dataset), '--no_plot',
                 '--recalculate_errors']) == 0

    saved_dir = synthetic_dataset / 'saved_results' / 'traj_est'
    assert saved_dir.is_dir()

    abs_files = list(saved_dir.glob('absolute_err_statistics_*.yaml'))
    assert len(abs_files) == 1
    abs_stats = _load_yaml(abs_files[0])
    assert set(abs_stats.keys()) == {'trans', 'rot', 'scale'}
    for stats in abs_stats.values():
        assert stats['num_samples'] > 0
        assert math.isfinite(stats['rmse'])

    rel_files = list(saved_dir.glob('relative_error_statistics_*.yaml'))
    assert len(rel_files) >= 1
    rel_stats = _load_yaml(rel_files[0])
    assert 'trans' in rel_stats
    assert rel_stats['trans']['num_samples'] > 0

    assert (saved_dir / 'cached' / 'cached_rel_err.pickle').is_file()

    report = synthetic_dataset / 'saved_results' / 'result.md'
    assert report.is_file()
    text = _report_text(report)
    assert '# 轨迹评估报告' in text
    assert '## 估计类型：`traj_est`' in text
    assert 'stamped_groundtruth.txt' in text
    assert 'stamped_traj_estimate.txt' in text
    assert '未生成图表' in text


def test_trajectory_public_api(synthetic_dataset):
    traj = Trajectory(str(synthetic_dataset))
    traj.compute_absolute_error()
    traj.compute_relative_errors()

    assert traj.abs_errors['abs_e_trans_stats']['num_samples'] > 0
    assert traj.rel_errors
    for errors in traj.rel_errors.values():
        assert 'rel_trans' in errors
        assert len(errors['rel_trans']) > 0


def test_explicit_trajectory_files_generate_report(synthetic_dataset):
    gt_path = synthetic_dataset / 'stamped_groundtruth.txt'
    est_path = synthetic_dataset / 'stamped_traj_estimate.txt'
    output_dir = synthetic_dataset / 'explicit_out'

    assert main([
        str(gt_path), str(est_path), '--no_plot',
        '--recalculate_errors', '--output_dir', str(output_dir)]) == 0

    report = output_dir / 'saved_results' / 'result.md'
    assert report.is_file()
    text = _report_text(report)
    assert str(gt_path) in text
    assert str(est_path) in text
    assert '## 估计类型：`traj_est`' in text


def test_auto_detects_custom_groundtruth_filename(synthetic_dataset):
    folder = synthetic_dataset / 'custom_names'
    folder.mkdir()
    shutil.copy2(synthetic_dataset / 'stamped_groundtruth.txt',
                 folder / 'GT.txt')
    shutil.copy2(synthetic_dataset / 'stamped_traj_estimate.txt',
                 folder / 'run_result.txt')
    shutil.copy2(synthetic_dataset / 'eval_cfg.yaml',
                 folder / 'eval_cfg.yaml')

    assert main([str(folder), '--no_plot', '--recalculate_errors']) == 0

    report = folder / 'saved_results' / 'result.md'
    assert report.is_file()
    text = _report_text(report)
    assert 'GT.txt' in text
    assert 'run_result.txt' in text
    assert '## 估计类型：`run_result`' in text


def test_interactive_selection_multiple_comparisons(
        synthetic_dataset, monkeypatch):
    folder = synthetic_dataset / 'prompt_comparison'
    folder.mkdir()
    shutil.copy2(synthetic_dataset / 'stamped_groundtruth.txt',
                 folder / 'groundtruth.txt')
    shutil.copy2(synthetic_dataset / 'stamped_traj_estimate.txt',
                 folder / 'a.txt')
    shutil.copy2(synthetic_dataset / 'stamped_traj_estimate.txt',
                 folder / 'b.txt')
    shutil.copy2(synthetic_dataset / 'eval_cfg.yaml', folder / 'eval_cfg.yaml')
    monkeypatch.setattr('builtins.input', lambda prompt='': '1')

    assert main([str(folder), '--no_plot', '--recalculate_errors']) == 0

    report = folder / 'saved_results' / 'result.md'
    assert report.is_file()
    text = _report_text(report)
    assert 'b.txt' in text
    assert (folder / 'saved_results' / 'b').is_dir()


def test_non_interactive_ambiguous_input_returns_error(
        synthetic_dataset, monkeypatch):
    folder = synthetic_dataset / 'non_interactive'
    folder.mkdir()
    shutil.copy2(synthetic_dataset / 'stamped_groundtruth.txt',
                 folder / 'GT.txt')
    shutil.copy2(synthetic_dataset / 'stamped_groundtruth.txt',
                 folder / 'groundtruth.txt')
    shutil.copy2(synthetic_dataset / 'stamped_traj_estimate.txt',
                 folder / 'estimate.txt')
    shutil.copy2(synthetic_dataset / 'eval_cfg.yaml', folder / 'eval_cfg.yaml')

    def _raise_eof(prompt=''):
        raise EOFError
    monkeypatch.setattr('builtins.input', _raise_eof)

    assert main([str(folder), '--no_plot']) == 1
    assert not (folder / 'saved_results' / 'result.md').exists()


def test_explicit_file_requires_comparison(synthetic_dataset):
    gt_path = synthetic_dataset / 'stamped_groundtruth.txt'
    assert main([str(gt_path), '--no_plot']) == 1


def test_explicit_file_rejects_mul_trials(synthetic_dataset):
    gt_path = synthetic_dataset / 'stamped_groundtruth.txt'
    est_path = synthetic_dataset / 'stamped_traj_estimate.txt'
    assert main([
        str(gt_path), str(est_path), '--mul_trials', '2', '--no_plot']) == 1


def test_legacy_est_types_mode(synthetic_dataset):
    folder = _make_dataset(
        synthetic_dataset / 'legacy_est_types', synthetic_dataset)
    shutil.copy2(folder / 'stamped_traj_estimate.txt',
                 folder / 'stamped_pose_graph_estimate.txt')

    assert main([
        str(folder), '--est_types', 'pose_graph',
        '--no_plot', '--recalculate_errors']) == 0

    assert (folder / 'saved_results' / 'pose_graph').is_dir()
    report = folder / 'saved_results' / 'result.md'
    assert report.is_file()
    assert '## 估计类型：`pose_graph`' in _report_text(report)


def test_legacy_multi_trial_mode(synthetic_dataset):
    folder = synthetic_dataset / 'legacy_multi_trial'
    folder.mkdir()
    shutil.copy2(synthetic_dataset / 'stamped_groundtruth.txt',
                 folder / 'stamped_groundtruth.txt')
    shutil.copy2(synthetic_dataset / 'stamped_traj_estimate.txt',
                 folder / 'stamped_traj_estimate0.txt')
    shutil.copy2(synthetic_dataset / 'stamped_traj_estimate.txt',
                 folder / 'stamped_traj_estimate1.txt')
    shutil.copy2(synthetic_dataset / 'eval_cfg.yaml', folder / 'eval_cfg.yaml')

    assert main([
        str(folder), '--mul_trials', '2',
        '--no_plot', '--recalculate_errors']) == 0

    report = folder / 'saved_results' / 'result.md'
    assert report.is_file()
    text = _report_text(report)
    assert '试验次数 | 2' in text
    assert '试验间统计' in text
    assert 'stamped_traj_estimate0.txt' in text
    assert 'stamped_traj_estimate1.txt' in text


def test_folder_input_with_separate_output_dir(synthetic_dataset):
    folder = _make_dataset(
        synthetic_dataset / 'separate_output_input', synthetic_dataset)
    output_dir = synthetic_dataset / 'separate_output'

    assert main([
        str(folder), '--no_plot', '--recalculate_errors',
        '--output_dir', str(output_dir)]) == 0

    report = output_dir / 'saved_results' / 'result.md'
    assert report.is_file()
    assert '输入目录 | `{0}`'.format(folder) in _report_text(report)
    assert not (folder / 'saved_results').exists()
