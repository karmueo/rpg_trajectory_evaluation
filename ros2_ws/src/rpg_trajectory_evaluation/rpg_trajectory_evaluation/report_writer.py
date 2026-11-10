#!/usr/bin/env python3
"""Write the Chinese Markdown result report for trajectory evaluation."""

import math
import os
from datetime import datetime

RESULT_REPORT_FILENAME = 'result.md'

_ALIGNMENT_DESCRIPTIONS = {
    'sim3': '相似变换对齐，包含尺度',
    'se3': '刚体变换对齐，不包含尺度',
    'posyaw': '位置与偏航角对齐',
    'none': '不做对齐',
}

# Longer prefixes must come first because they share a common prefix with
# shorter entries (e.g. scale_error_traj vs. scale_error).  Each entry
# describes the coordinate system and the curves shown in the figure.
_PLOT_METADATA = [
    ('scale_error_traj', {
        'title': '尺度误差轨迹着色图',
        'coordinate_system': '上图：x-y 平面（横轴 x [m]，纵轴 y [m]）；'
                             '下图：x-z 平面（横轴 x [m]，纵轴 z [m]）',
        'curves': '真值轨迹曲线；颜色表示对应位置的尺度误差大小，'
                  '使用 jet 色图（蓝色误差小，红色误差大）',
    }),
    ('rel_translation_error_perc', {
        'title': '相对平移误差百分比箱线图',
        'coordinate_system': '横轴：子轨迹长度 [m]；纵轴：相对平移误差 [%]',
        'curves': '蓝色箱线图：各子轨迹上的相对平移误差百分比分布',
    }),
    ('rel_translation_error', {
        'title': '相对平移误差箱线图',
        'coordinate_system': '横轴：子轨迹长度 [m]；纵轴：相对平移误差 [m]',
        'curves': '蓝色箱线图：各子轨迹上的相对平移误差分布',
    }),
    ('rel_yaw_error', {
        'title': '相对偏航误差箱线图',
        'coordinate_system': '横轴：子轨迹长度 [m]；纵轴：相对偏航误差 [deg]',
        'curves': '蓝色箱线图：各子轨迹上的相对偏航误差分布',
    }),
    ('trajectory_3d_gt', {
        'title': '真值轨迹三维图',
        'coordinate_system': '三维坐标系：横轴 x [m]，纵轴 y [m]，竖轴 z [m]',
        'curves': '品红色曲线：真值轨迹',
    }),
    ('trajectory_3d', {
        'title': '真值与对比轨迹三维图',
        'coordinate_system': '三维坐标系：横轴 x [m]，纵轴 y [m]，竖轴 z [m]',
        'curves': '蓝色曲线：对齐后的对比轨迹；品红色曲线：真值轨迹',
    }),
    ('trajectory_top', {
        'title': '轨迹俯视图',
        'coordinate_system': 'x-y 平面（横轴 x [m]，纵轴 y [m]）',
        'curves': '蓝色曲线：对齐后的对比轨迹；品红色曲线：真值轨迹；'
                  '灰色短线：对齐后的对应点连线',
    }),
    ('trajectory_side', {
        'title': '轨迹侧视图',
        'coordinate_system': 'x-z 平面（横轴 x [m]，纵轴 z [m]）',
        'curves': '蓝色曲线：对齐后的对比轨迹；品红色曲线：真值轨迹',
    }),
    ('translation_error', {
        'title': '平移误差随距离变化',
        'coordinate_system': '横轴：累计距离 [m]；纵轴：位置漂移 [mm]',
        'curves': '红色、绿色、蓝色曲线分别表示 x、y、z 方向的位置误差',
    }),
    ('rotation_error', {
        'title': '旋转误差随距离变化',
        'coordinate_system': '横轴：累计距离 [m]；纵轴：姿态误差 [deg]',
        'curves': '红色、绿色、蓝色曲线分别表示 yaw、pitch、roll 姿态误差',
    }),
    ('scale_error', {
        'title': '尺度误差随距离变化',
        'coordinate_system': '横轴：累计距离 [m]；纵轴：尺度漂移 [%]',
        'curves': '蓝色曲线：尺度误差',
    }),
    ('mt_abs_err', {
        'title': '多试验绝对误差统计',
        'coordinate_system': '—',
        'curves': '—',
    }),
]

_STAT_ROWS = [
    ('rmse', 'RMSE'),
    ('mean', '均值'),
    ('median', '中位数'),
    ('std', '标准差'),
    ('min', '最小值'),
    ('max', '最大值'),
]


def _fmt(value, digits=4):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return '—'
    if not math.isfinite(value):
        return '—'
    return '{0:.{1}f}'.format(value, digits)


def _fmt_int(value):
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return '—'


def _md_cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def _path_cell(paths):
    if isinstance(paths, str):
        paths = [paths]
    if not paths:
        return '—'
    return '<br>'.join('`{0}`'.format(_md_cell(path)) for path in paths)


def _alignment_label(align_type):
    description = _ALIGNMENT_DESCRIPTIONS.get(align_type)
    if description:
        return '`{0}`（{1}）'.format(align_type, description)
    return '`{0}`'.format(align_type)


def _align_frames_label(frames):
    try:
        frames = int(frames)
    except (TypeError, ValueError):
        return '—'
    if frames < 0:
        return '全部位姿'
    return str(frames)


def _plot_metadata(path):
    basename = os.path.basename(path)
    for prefix, metadata in _PLOT_METADATA:
        if basename.startswith(prefix):
            return metadata
    return {
        'title': basename,
        'coordinate_system': '—',
        'curves': '—',
    }


def _plot_link(path, report_dir):
    path_abs = os.path.abspath(path)
    if report_dir is None:
        return path_abs
    try:
        relative = os.path.relpath(path_abs, os.path.abspath(report_dir))
    except ValueError:
        return path_abs
    return relative.replace(os.sep, '/')


def _stats_value(stats, key, digits=4):
    if not stats:
        return '—'
    return _fmt(stats.get(key), digits)


def _render_text_stats_table(stats, include_scale):
    lines = []
    header = '| 统计量 | 平移误差 (m) | 旋转误差 (deg) |'
    separator = '| --- | ---: | ---: |'
    if include_scale:
        header += ' 尺度误差 (%) |'
        separator += ' ---: |'
    lines.extend([header, separator])
    for key, label in _STAT_ROWS:
        row = '| {0} | {1} | {2} |'.format(
            label, _stats_value(stats.get('trans'), key),
            _stats_value(stats.get('rot'), key))
        if include_scale:
            row += ' {0} |'.format(_stats_value(stats.get('scale'), key))
        lines.append(row)
    row = '| 样本数 | {0} | {1} |'.format(
        _fmt_int((stats.get('trans') or {}).get('num_samples')),
        _fmt_int((stats.get('rot') or {}).get('num_samples')))
    if include_scale:
        row += ' {0} |'.format(
            _fmt_int((stats.get('scale') or {}).get('num_samples')))
    lines.append(row)
    return lines


def _render_trial_table(entry, include_scale):
    trials = entry.get('trial_stats') or []
    if not trials:
        return []
    header = ('| 试验 | 匹配位姿数 | 真值长度 (m) | 对比长度 (m) | '
              '平移 RMSE (m) | 旋转 RMSE (deg) | 终点误差 (m) |')
    separator = '| ---: | ---: | ---: | ---: | ---: | ---: | ---: |'
    if include_scale:
        header += ' 尺度 |'
        separator += ' ---: |'
    lines = [header, separator]
    for trial in trials:
        row = '| {0} | {1} | {2} | {3} | {4} | {5} | {6} |'.format(
            _fmt_int(trial.get('index')),
            _fmt_int(trial.get('num_matches')),
            _fmt(trial.get('gt_length'), 3),
            _fmt(trial.get('est_length'), 3),
            _fmt(trial.get('trans_rmse')),
            _fmt(trial.get('rot_rmse')),
            _fmt(trial.get('end_error')))
        if include_scale:
            row += ' {0} |'.format(_fmt(trial.get('scale'), 4))
        lines.append(row)
    return lines


def _render_rpe_table(rel_stats):
    distances = sorted(rel_stats) if rel_stats else []
    if not distances:
        return ['无可用的相对轨迹误差结果。']

    lines = [
        '| 子轨迹长度 (m) | 平移 RMSE (m) | 平移 RMSE (%) | '
        '偏航 RMSE (deg) | 旋转 RMSE (deg/m) |',
        '| ---: | ---: | ---: | ---: | ---: |',
    ]
    for distance in distances:
        stats = rel_stats[distance]
        lines.append('| {0} | {1} | {2} | {3} | {4} |'.format(
            _fmt(distance, 2),
            _stats_value(stats.get('trans'), 'rmse'),
            _stats_value(stats.get('trans_perc'), 'rmse'),
            _stats_value(stats.get('yaw'), 'rmse'),
            _stats_value(stats.get('rot_deg_per_m'), 'rmse')))
    return lines


def _render_plot_section(entry, report_dir):
    plots = entry.get('plots') or []
    if not plots:
        return ['本次运行未生成图表。']
    lines = []
    for index, path in enumerate(plots, 1):
        metadata = _plot_metadata(path)
        title = metadata['title']
        link = _plot_link(path, report_dir)
        lines.extend([
            '#### 图 {0}：{1}'.format(index, title),
            '',
            '| 项目 | 说明 |',
            '| --- | --- |',
            '| 坐标系 | {0} |'.format(
                _md_cell(metadata['coordinate_system'])),
            '| 曲线 | {0} |'.format(_md_cell(metadata['curves'])),
            '',
        ])
        if os.path.splitext(path)[1].lower() == '.png':
            lines.append('![{0}](<{1}>)'.format(title, link))
        else:
            lines.append('[图 {0}：{1}（PDF）](<{2}>)'.format(
                index, title, link))
        lines.append('')
    return lines


def _render_input_section(entry):
    align_type = entry.get('align_type') or '—'
    if align_type == '—':
        alignment = '—'
    else:
        alignment = _alignment_label(align_type)
    success_indices = entry.get('success_indices') or []
    return [
        '| 项目 | 内容 |',
        '| --- | --- |',
        '| 真值轨迹 | {0} |'.format(
            _path_cell(entry.get('gt_path') or [])),
        '| 对比轨迹 | {0} |'.format(
            _path_cell(entry.get('est_paths') or [])),
        '| 输入目录 | {0} |'.format(
            _path_cell(entry.get('input_dir') or [])),
        '| 输出目录 | {0} |'.format(
            _path_cell(entry.get('output_dir') or [])),
        '| 对齐方式 | {0} |'.format(alignment),
        '| 对齐帧数 | {0} |'.format(
            _align_frames_label(entry.get('align_num_frames'))),
        '| 试验次数 | {0} |'.format(
            _fmt_int(entry.get('n_trials'))),
        '| 成功试验编号 | {0} |'.format(
            '、'.join(str(index) for index in success_indices) or '—'),
    ]


def _render_trajectory_summary(entry):
    trials = entry.get('trial_stats') or []
    if not trials:
        return []
    first = trials[0]
    align_type = entry.get('align_type')
    lines = [
        '| 项目 | 数值 |',
        '| --- | ---: |',
        '| 匹配位姿数 | {0} |'.format(
            _fmt_int(first.get('num_matches'))),
        '| 真值轨迹长度 | {0} m |'.format(
            _fmt(first.get('gt_length'), 3)),
        '| 对齐后对比轨迹长度 | {0} m |'.format(
            _fmt(first.get('est_length'), 3)),
        '| 长度偏差 | {0}% |'.format(
            _fmt(first.get('length_diff_perc'), 3)),
        '| 终点位置误差 | {0} m |'.format(
            _fmt(first.get('end_error'))),
        '| 时间范围 | {0} s ~ {1} s |'.format(
            _fmt(first.get('time_start'), 6),
            _fmt(first.get('time_end'), 6)),
    ]
    if align_type == 'sim3':
        lines.append('| 尺度因子 | {0} |'.format(
            _fmt(first.get('scale'), 4)))
    return lines


def _render_entry(entry, report_dir):
    est_type = entry.get('est_type') or 'unknown'
    lines = ['## 估计类型：`{0}`'.format(est_type), '',
             '### 输入与配置', '']
    lines.extend(_render_input_section(entry))
    lines.append('')

    if not entry.get('success', True):
        lines.extend([
            '### 评估失败', '',
            entry.get(
                'failure_reason',
                '未能成功加载、匹配或对齐轨迹。请检查轨迹格式、时间戳，'
                '以及真值轨迹和对比轨迹是否对应。'),
            '',
        ])
        return lines

    align_type = entry.get('align_type')
    include_scale = align_type == 'sim3'
    trials = entry.get('trial_stats') or []
    n_trials = int(entry.get('n_trials') or 1)
    abs_stats = entry.get('abs_stats') or {}
    rel_stats = entry.get('rel_stats') or {}

    if n_trials == 1 and trials:
        lines.extend(['### 轨迹概况', ''])
        lines.extend(_render_trajectory_summary(entry))
        lines.append('')

    lines.extend(['### 绝对轨迹误差（ATE）', ''])
    if n_trials == 1:
        lines.extend(_render_text_stats_table(abs_stats, include_scale))
    else:
        lines.extend(['#### 各次试验', ''])
        lines.extend(_render_trial_table(entry, include_scale))
        lines.extend(['', '#### 试验间统计', ''])
        lines.extend(_render_text_stats_table(abs_stats, include_scale))
    lines.append('')

    lines.extend(['### 相对轨迹误差（RPE，KITTI 风格）', ''])
    lines.extend(_render_rpe_table(rel_stats))
    lines.append('')

    lines.extend(['### 图表', ''])
    lines.extend(_render_plot_section(entry, report_dir))
    lines.append('')
    return lines


def build_markdown_report(entries, report_dir=None, generated_at=None):
    """Return the Chinese Markdown report as a string."""
    if generated_at is None:
        generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    entries = list(entries)
    output_dir = entries[0].get('output_dir') if entries else None

    lines = [
        '# 轨迹评估报告',
        '',
        '| 项目 | 内容 |',
        '| --- | --- |',
        '| 生成时间 | {0} |'.format(generated_at),
        '| 输出目录 | {0} |'.format(
            _path_cell(output_dir) if output_dir else '—'),
        '| 评估估计类型数 | {0} |'.format(len(entries)),
        '',
    ]
    if not entries:
        lines.extend(['没有可用的评估结果。', ''])
        return '\n'.join(lines).rstrip() + '\n'

    for entry in entries:
        lines.extend(_render_entry(entry, report_dir))
    return '\n'.join(lines).rstrip() + '\n'


def write_markdown_report(report_path, entries):
    """Write the Markdown report and return the report path."""
    report_path = os.path.abspath(report_path)
    report_dir = os.path.dirname(report_path)
    if not os.path.isdir(report_dir):
        os.makedirs(report_dir, exist_ok=True)
    text = build_markdown_report(entries, report_dir=report_dir)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(text)
    return report_path
