#!/usr/bin/env python3
"""Discover and select trajectory files for single-trajectory evaluation."""

import os
import re
from dataclasses import dataclass
from typing import Optional

from rpg_trajectory_evaluation.fn_constants import (
    kNsToEstFnMapping, kNsToMatchFnMapping)

DEFAULT_EST_LABEL = 'traj_est'
DEFAULT_MATCH_PREFIX = 'stamped_est_gt_matches'

_GT_NAME_PATTERN = re.compile(r'ground[_\-\s]?truth')
_TOKEN_SPLIT_PATTERN = re.compile(r'[^a-z0-9]+')
_TRAJECTORY_EXTENSION = '.txt'
_MIN_TRAJECTORY_COLUMNS = 8
_MAX_SELECTION_ATTEMPTS = 5


class InputResolutionError(Exception):
    """Raised when the input trajectories cannot be resolved."""


@dataclass(frozen=True)
class ResolvedInputs:
    """Paths selected for a single evaluation run."""

    gt_path: str
    est_path: Optional[str]
    data_dir: str
    output_dir: str
    est_label: Optional[str]
    folder_input: bool = False


def is_groundtruth_filename(filename):
    """Return True if a filename looks like a groundtruth trajectory."""
    stem = os.path.splitext(os.path.basename(filename))[0].lower()
    if _GT_NAME_PATTERN.search(stem):
        return True
    tokens = [token for token in _TOKEN_SPLIT_PATTERN.split(stem) if token]
    return 'gt' in tokens


def is_trajectory_file(path):
    """Return True if the file looks like a stamped trajectory text file.

    A stamped trajectory has at least eight whitespace separated numeric
    fields per line (timestamp, position and quaternion).  Blank lines and
    comments starting with ``#`` are skipped; only the first data line is
    checked so that scanning a folder stays cheap.
    """
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                fields = line.split()
                if len(fields) < _MIN_TRAJECTORY_COLUMNS:
                    return False
                try:
                    [float(field) for field in fields[:_MIN_TRAJECTORY_COLUMNS]]
                except ValueError:
                    return False
                return True
    except OSError:
        return False
    return False


def discover_trajectory_files(folder):
    """Return sorted absolute paths of trajectory files in ``folder``.

    Only regular ``.txt`` files directly inside ``folder`` are considered.
    Files that do not look like stamped trajectories are skipped with a
    short notice.
    """
    folder = os.path.abspath(folder)
    try:
        entries = sorted(os.scandir(folder), key=lambda entry: entry.name)
    except OSError as e:
        raise InputResolutionError(
            "无法读取轨迹文件夹 {0}: {1}".format(folder, e))

    trajectory_files = []
    for entry in entries:
        if not entry.is_file():
            continue
        if os.path.splitext(entry.name)[1].lower() != _TRAJECTORY_EXTENSION:
            continue
        path = os.path.abspath(entry.path)
        if is_trajectory_file(path):
            trajectory_files.append(path)
        else:
            print("[提示] 跳过非轨迹文件：{0}".format(entry.name))
    return trajectory_files


def derive_est_label(est_path):
    """Derive the estimation-type label used for output subdirectories."""
    stem = os.path.splitext(os.path.basename(est_path))[0]
    for est_type, base_name in kNsToEstFnMapping.items():
        if re.fullmatch(re.escape(base_name) + r'\d*', stem):
            return est_type

    label = re.sub(r'[^0-9A-Za-z_\-]+', '_', stem).strip('_')
    return label if label else DEFAULT_EST_LABEL


def match_filename_prefix(est_label):
    """Return the match-file prefix for an estimation-type label."""
    return kNsToMatchFnMapping.get(est_label, DEFAULT_MATCH_PREFIX)


def _candidate_lines(files, gt_candidates):
    gt_set = set(gt_candidates)
    lines = []
    for index, path in enumerate(files):
        role = '疑似真值' if path in gt_set else '疑似对比'
        lines.append("  [{0}] {1}（{2}）".format(
            index, os.path.basename(path), role))
    return lines


def _print_candidates(files, gt_candidates, title):
    print(title)
    for line in _candidate_lines(files, gt_candidates):
        print(line)
    if not gt_candidates:
        print("  提示：没有文件名匹配 groundtruth / ground_truth / gt 规则。")


def _read_choice(prompt, num_candidates, default_index, input_fn):
    if input_fn is None:
        input_fn = input

    for attempt in range(_MAX_SELECTION_ATTEMPTS):
        try:
            raw = input_fn(prompt)
        except EOFError:
            raise InputResolutionError(
                "当前环境无法读取交互输入，请显式传入真值轨迹和对比轨迹文件路径。")
        raw = (raw or '').strip()
        if raw == '':
            return default_index
        try:
            index = int(raw)
        except ValueError:
            print("请输入候选轨迹的编号（0-{0}）。".format(
                num_candidates - 1))
            continue
        if index < 0 or index >= num_candidates:
            print("编号超出范围（0-{0}），请重新输入。".format(
                num_candidates - 1))
            continue
        return index

    raise InputResolutionError(
        "连续 {0} 次输入无效，已取消轨迹选择。".format(
            _MAX_SELECTION_ATTEMPTS))


def _select_groundtruth(files, gt_candidates, input_fn=None):
    if len(gt_candidates) == 1:
        return gt_candidates[0]

    if not gt_candidates:
        print("警告：未能根据文件名自动识别真值轨迹。")

    _print_candidates(files, gt_candidates, "请选择真值轨迹：")
    default_index = files.index(gt_candidates[0]) if gt_candidates else 0
    index = _read_choice(
        "真值轨迹编号 [默认 {0}]: ".format(default_index),
        len(files), default_index, input_fn)
    return files[index]


def _select_comparison(files, gt_path, gt_candidates, input_fn=None):
    # Prefer files that are not groundtruth candidates; the remaining
    # trajectories are the natural comparison candidates.
    non_gt_candidates = [
        path for path in files
        if path != gt_path and path not in set(gt_candidates)]
    if non_gt_candidates:
        candidates = non_gt_candidates
    else:
        candidates = [path for path in files if path != gt_path]
    if not candidates:
        raise InputResolutionError(
            "文件夹中只有真值轨迹，未找到用于对比的轨迹文件。")
    if len(candidates) == 1:
        return candidates[0]

    print("请选择对比轨迹：")
    gt_set = set(gt_candidates)
    for index, path in enumerate(candidates):
        role = '疑似真值' if path in gt_set else '疑似对比'
        print("  [{0}] {1}（{2}）".format(
            index, os.path.basename(path), role))
    index = _read_choice(
        "对比轨迹编号 [默认 0]: ", len(candidates), 0, input_fn)
    return candidates[index]


def _validate_explicit_files(gt_path, est_path):
    for label, path in (('真值轨迹', gt_path), ('对比轨迹', est_path)):
        if not os.path.isfile(path):
            raise InputResolutionError(
                "{0}文件不存在：{1}".format(label, path))
        if not is_trajectory_file(path):
            raise InputResolutionError(
                "{0}不是有效的轨迹文件（需要至少 8 列数值）：{1}".format(
                    label, path))
    if os.path.abspath(gt_path) == os.path.abspath(est_path):
        raise InputResolutionError("真值轨迹和对比轨迹不能是同一个文件。")


def resolve_inputs(input_path, comparison_path=None, output_dir=None,
                   resolve_comparison=True, input_fn=None):
    """Resolve input arguments into explicit trajectory paths.

    Args:
        input_path: A result folder or a groundtruth trajectory file.
        comparison_path: Optional explicit comparison trajectory file.
        output_dir: Optional directory for ``saved_results`` and ``plots``.
        resolve_comparison: If False, only locate the groundtruth file.  This
            is used by the legacy ``--est_types`` / ``--mul_trials`` mode.
        input_fn: Optional function used for interactive selection.  It is
            mainly useful for tests; ``input`` is used when omitted.

    Returns:
        A :class:`ResolvedInputs` instance.
    """
    input_abs = os.path.abspath(input_path)
    if not os.path.exists(input_abs):
        raise InputResolutionError("输入路径不存在：{0}".format(input_path))

    output_abs = None
    if output_dir:
        output_abs = os.path.abspath(output_dir)
        if os.path.exists(output_abs) and not os.path.isdir(output_abs):
            raise InputResolutionError(
                "--output_dir 必须是目录：{0}".format(output_abs))

    if os.path.isfile(input_abs):
        if not resolve_comparison:
            raise InputResolutionError(
                "文件输入模式需要同时指定真值轨迹和对比轨迹文件。")
        if not comparison_path:
            raise InputResolutionError(
                "当第一个参数是轨迹文件时，必须提供对比轨迹文件路径。")
        gt_path = input_abs
        est_path = os.path.abspath(comparison_path)
        _validate_explicit_files(gt_path, est_path)
        data_dir = os.path.dirname(est_path)
        return ResolvedInputs(
            gt_path=gt_path,
            est_path=est_path,
            data_dir=data_dir,
            output_dir=output_abs or data_dir,
            est_label=derive_est_label(est_path),
            folder_input=False)

    if not os.path.isdir(input_abs):
        raise InputResolutionError(
            "输入路径既不是文件夹也不是轨迹文件：{0}".format(input_path))

    files = discover_trajectory_files(input_abs)
    if not files:
        raise InputResolutionError(
            "文件夹中未找到有效的轨迹文件（.txt）：{0}".format(input_abs))

    gt_candidates = [path for path in files
                     if is_groundtruth_filename(path)]
    gt_path = _select_groundtruth(files, gt_candidates, input_fn)

    if resolve_comparison:
        if comparison_path:
            est_path = os.path.abspath(comparison_path)
            _validate_explicit_files(gt_path, est_path)
        else:
            est_path = _select_comparison(
                files, gt_path, gt_candidates, input_fn)
        est_label = derive_est_label(est_path)
    else:
        est_path = None
        est_label = None

    return ResolvedInputs(
        gt_path=gt_path,
        est_path=est_path,
        data_dir=input_abs,
        output_dir=output_abs or input_abs,
        est_label=est_label,
        folder_input=True)
