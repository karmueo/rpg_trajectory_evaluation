import numpy as np
import pytest

from rpg_trajectory_evaluation.trajectory_discovery import (
    InputResolutionError, derive_est_label, discover_trajectory_files,
    is_groundtruth_filename, match_filename_prefix, resolve_inputs)


def _write_traj(path, value=0.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 5
    timestamps = np.arange(n, dtype=float)
    zeros = np.zeros(n, dtype=float)
    ones = np.ones(n, dtype=float)
    data = np.column_stack([
        timestamps, np.full(n, value), zeros, zeros,
        zeros, zeros, zeros, ones,
    ])
    np.savetxt(str(path), data, fmt='%.9f')


def _input_fn(values):
    values = list(values)

    def _fn(prompt=''):
        if not values:
            raise EOFError
        return values.pop(0)
    return _fn


@pytest.mark.parametrize('name', [
    'groundtruth.txt',
    'stamped_groundtruth.txt',
    'ground_truth.txt',
    'gt.txt',
    'GT.txt',
    'stamped_gt.txt',
    'pose_gt.txt',
    'gt_pose.txt',
])
def test_groundtruth_filename_rules(name):
    assert is_groundtruth_filename(name)


@pytest.mark.parametrize('name', [
    'estimate.txt',
    'target.txt',
    'stamped_traj_estimate.txt',
    'result_gtless.txt',
])
def test_non_groundtruth_filename_rules(name):
    assert not is_groundtruth_filename(name)


def test_discover_skips_non_trajectory_files(tmp_path, capsys):
    _write_traj(tmp_path / 'GT.txt')
    _write_traj(tmp_path / 'estimate.txt')
    (tmp_path / 'notes.txt').write_text('a b\n1 2\n')
    (tmp_path / 'readme.md').write_text('not a trajectory\n')

    files = discover_trajectory_files(str(tmp_path))

    assert [p.split('/')[-1] for p in files] == ['GT.txt', 'estimate.txt']
    assert '跳过非轨迹文件' in capsys.readouterr().out


def test_discover_accepts_comment_header(tmp_path):
    gt = tmp_path / 'groundtruth.txt'
    _write_traj(gt)
    content = gt.read_text()
    gt.write_text('# time x y z qx qy qz qw\n' + content)
    est = tmp_path / 'estimate.txt'
    _write_traj(est)

    files = discover_trajectory_files(str(tmp_path))

    assert {p.split('/')[-1] for p in files} == {'groundtruth.txt',
                                                 'estimate.txt'}


def test_resolve_folder_auto_unique(tmp_path):
    gt = tmp_path / 'groundtruth.txt'
    est = tmp_path / 'estimate.txt'
    _write_traj(gt)
    _write_traj(est)

    resolved = resolve_inputs(str(tmp_path))

    assert resolved.gt_path == str(gt)
    assert resolved.est_path == str(est)
    assert resolved.data_dir == str(tmp_path)
    assert resolved.output_dir == str(tmp_path)
    assert resolved.est_label == 'estimate'
    assert resolved.folder_input


def test_resolve_explicit_files_defaults_to_estimate_dir(tmp_path):
    gt_dir = tmp_path / 'gt'
    est_dir = tmp_path / 'est'
    gt = gt_dir / 'my_groundtruth.txt'
    est = est_dir / 'stamped_traj_estimate.txt'
    _write_traj(gt)
    _write_traj(est)

    resolved = resolve_inputs(str(gt), str(est))

    assert resolved.gt_path == str(gt)
    assert resolved.est_path == str(est)
    assert resolved.data_dir == str(est_dir)
    assert resolved.output_dir == str(est_dir)
    assert resolved.est_label == 'traj_est'
    assert not resolved.folder_input


def test_resolve_explicit_files_with_output_dir(tmp_path):
    gt = tmp_path / 'gt.txt'
    est = tmp_path / 'est.txt'
    out = tmp_path / 'out'
    _write_traj(gt)
    _write_traj(est)

    resolved = resolve_inputs(str(gt), str(est), output_dir=str(out))

    assert resolved.output_dir == str(out)
    assert resolved.data_dir == str(tmp_path)
    assert resolved.est_label == 'est'


def test_resolve_folder_prompts_for_groundtruth(tmp_path):
    _write_traj(tmp_path / 'GT.txt')
    _write_traj(tmp_path / 'estimate.txt')
    _write_traj(tmp_path / 'groundtruth.txt')

    resolved = resolve_inputs(
        str(tmp_path), input_fn=_input_fn(['2']))

    assert resolved.gt_path.endswith('groundtruth.txt')
    assert resolved.est_path.endswith('estimate.txt')


def test_resolve_folder_prompts_for_comparison(tmp_path):
    _write_traj(tmp_path / 'GT.txt')
    _write_traj(tmp_path / 'first.txt')
    _write_traj(tmp_path / 'second.txt')

    resolved = resolve_inputs(
        str(tmp_path), input_fn=_input_fn(['1']))

    assert resolved.gt_path.endswith('GT.txt')
    assert resolved.est_path.endswith('second.txt')


def test_resolve_folder_with_explicit_comparison(tmp_path):
    _write_traj(tmp_path / 'GT.txt')
    external = tmp_path / 'external' / 'result.txt'
    _write_traj(external)

    resolved = resolve_inputs(str(tmp_path), str(external))

    assert resolved.gt_path.endswith('GT.txt')
    assert resolved.est_path == str(external)
    assert resolved.est_label == 'result'
    assert resolved.output_dir == str(tmp_path)


def test_resolve_folder_retries_invalid_selection(tmp_path, capsys):
    _write_traj(tmp_path / 'GT.txt')
    _write_traj(tmp_path / 'a.txt')
    _write_traj(tmp_path / 'groundtruth.txt')

    resolved = resolve_inputs(
        str(tmp_path), input_fn=_input_fn(['bad', '99', '2']))

    assert resolved.gt_path.endswith('groundtruth.txt')
    assert resolved.est_path.endswith('a.txt')
    output = capsys.readouterr().out
    assert '请输入候选轨迹的编号' in output
    assert '编号超出范围' in output


def test_resolve_folder_eof_raises(tmp_path):
    _write_traj(tmp_path / 'GT.txt')
    _write_traj(tmp_path / 'a.txt')
    _write_traj(tmp_path / 'groundtruth.txt')

    with pytest.raises(InputResolutionError):
        resolve_inputs(str(tmp_path), input_fn=_input_fn([]))


def test_resolve_file_requires_comparison(tmp_path):
    gt = tmp_path / 'gt.txt'
    _write_traj(gt)

    with pytest.raises(InputResolutionError):
        resolve_inputs(str(gt))


def test_resolve_rejects_same_file(tmp_path):
    gt = tmp_path / 'gt.txt'
    _write_traj(gt)

    with pytest.raises(InputResolutionError):
        resolve_inputs(str(gt), str(gt))


def test_resolve_rejects_invalid_trajectory(tmp_path):
    gt = tmp_path / 'gt.txt'
    est = tmp_path / 'est.txt'
    _write_traj(gt)
    est.write_text('not a trajectory\n')

    with pytest.raises(InputResolutionError):
        resolve_inputs(str(gt), str(est))


@pytest.mark.parametrize('filename,expected', [
    ('stamped_traj_estimate.txt', 'traj_est'),
    ('stamped_traj_estimate3.txt', 'traj_est'),
    ('stamped_pose_graph_estimate.txt', 'pose_graph'),
    ('my_est.txt', 'my_est'),
    ('weird name!.txt', 'weird_name'),
])
def test_derive_est_label(tmp_path, filename, expected):
    assert derive_est_label(str(tmp_path / filename)) == expected


def test_match_filename_prefix_fallback():
    assert match_filename_prefix('traj_est') == 'stamped_est_gt_matches'
    assert match_filename_prefix('unknown_type') == 'stamped_est_gt_matches'
