import os

from rpg_trajectory_evaluation.report_writer import (
    build_markdown_report, write_markdown_report)


def _stats(rmse, num_samples=100):
    return {
        'rmse': rmse,
        'mean': rmse * 0.9,
        'median': rmse * 0.8,
        'std': rmse * 0.1,
        'min': 0.0,
        'max': rmse * 2.0,
        'num_samples': num_samples,
    }


def _entry(align_type='se3', n_trials=1, success=True):
    trials = []
    for index in range(n_trials):
        trials.append({
            'index': index,
            'num_matches': 300,
            'gt_length': 20.0,
            'est_length': 19.5,
            'length_diff_perc': -2.5,
            'end_error': 0.05,
            'scale': 1.01,
            'time_start': 1.0,
            'time_end': 21.0,
            'trans_rmse': 0.123,
            'rot_rmse': 0.456,
            'scale_rmse': 0.789,
        })
    return {
        'est_type': 'traj_est',
        'gt_path': '/data/groundtruth.txt',
        'est_paths': ['/data/stamped_traj_estimate.txt'],
        'input_dir': '/data',
        'output_dir': '/data',
        'align_type': align_type,
        'align_num_frames': -1,
        'n_trials': n_trials,
        'success_indices': list(range(n_trials)) if success else [],
        'success': success,
        'abs_stats': {
            'trans': _stats(0.123, n_trials),
            'rot': _stats(0.456, n_trials),
            'scale': _stats(0.789, n_trials),
        },
        'rel_stats': {
            2.0: {
                'trans': _stats(0.01),
                'trans_perc': _stats(0.5),
                'yaw': _stats(0.2),
                'rot_deg_per_m': _stats(0.1),
            },
            4.0: {
                'trans': _stats(0.02),
                'trans_perc': _stats(0.4),
                'yaw': _stats(0.3),
                'rot_deg_per_m': _stats(0.05),
            },
        },
        'trial_stats': trials,
        'plots': [],
    }


def test_build_markdown_report_single_trial(tmp_path):
    plot = os.path.join(str(tmp_path), 'plots', 'trajectory_top_se3_-1.png')
    entry = _entry()
    entry['plots'] = [plot]

    text = build_markdown_report(
        [entry], report_dir=str(tmp_path), generated_at='2026-01-02 03:04:05')

    assert text.startswith('# 轨迹评估报告')
    assert '| 生成时间 | 2026-01-02 03:04:05 |' in text
    assert '## 估计类型：`traj_est`' in text
    assert '绝对轨迹误差（ATE）' in text
    assert '相对轨迹误差（RPE，KITTI 风格）' in text
    assert '对比分析' not in text
    assert '共匹配' not in text
    assert '0.1230' in text
    assert '#### 图 1：轨迹俯视图' in text
    assert '| 坐标系 | x-y 平面（横轴 x [m]，纵轴 y [m]） |' in text
    assert '| 曲线 | 蓝色曲线：对齐后的对比轨迹' in text
    assert '![轨迹俯视图](<plots/trajectory_top_se3_-1.png>)' in text
    assert '尺度误差 (%)' not in text


def test_build_markdown_report_sim3_includes_scale(tmp_path):
    text = build_markdown_report(
        [_entry(align_type='sim3')], report_dir=str(tmp_path))

    assert '尺度误差 (%)' in text
    assert '尺度因子 | 1.0100' in text
    assert '相似变换对齐' in text


def test_build_markdown_report_multi_trial(tmp_path):
    text = build_markdown_report(
        [_entry(n_trials=3)], report_dir=str(tmp_path))

    assert '试验次数 | 3' in text
    assert '#### 各次试验' in text
    assert '#### 试验间统计' in text
    assert '对比分析' not in text
    assert '| 0 | 300 |' in text
    assert '| 2 | 300 |' in text


def test_build_markdown_report_failure(tmp_path):
    entry = _entry(success=False)
    entry.update({
        'abs_stats': None,
        'rel_stats': {},
        'trial_stats': [],
        'align_type': None,
        'failure_reason': '测试失败原因。',
    })

    text = build_markdown_report([entry], report_dir=str(tmp_path))

    assert '### 评估失败' in text
    assert '测试失败原因。' in text
    assert '绝对轨迹误差' not in text


def test_build_markdown_report_handles_missing_values(tmp_path):
    entry = _entry()
    entry['abs_stats']['trans']['rmse'] = float('nan')
    entry['trial_stats'][0]['gt_length'] = float('nan')

    text = build_markdown_report([entry], report_dir=str(tmp_path))

    assert '—' in text


def test_write_markdown_report_utf8(tmp_path):
    report_path = tmp_path / 'saved_results' / 'result.md'
    written = write_markdown_report(str(report_path), [_entry()])

    assert written == str(report_path)
    assert report_path.is_file()
    text = report_path.read_text(encoding='utf-8')
    assert '# 轨迹评估报告' in text
