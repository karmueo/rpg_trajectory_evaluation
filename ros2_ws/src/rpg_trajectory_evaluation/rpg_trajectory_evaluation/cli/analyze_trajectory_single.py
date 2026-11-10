#!/usr/bin/env python3

import os
import sys
import shutil
import argparse

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from colorama import init, Fore

from rpg_trajectory_evaluation import plot_utils as pu
from rpg_trajectory_evaluation import trajectory_utils as traj_utils
from rpg_trajectory_evaluation.fn_constants import (
    kNsToEstFnMapping, kNsToMatchFnMapping, kFnExt)
from rpg_trajectory_evaluation.multiple_traj_errors import MulTrajError
from rpg_trajectory_evaluation.report_writer import (
    RESULT_REPORT_FILENAME, write_markdown_report)
from rpg_trajectory_evaluation.trajectory import Trajectory
from rpg_trajectory_evaluation.trajectory_discovery import (
    InputResolutionError, match_filename_prefix, resolve_inputs)

init(autoreset=True)

FORMAT = '.png'
DPI = 200


def save_figure(fig, filename):
    """Save a figure using the selected format and a reasonable resolution."""
    fig.savefig(filename, bbox_inches="tight", dpi=DPI)


def analyze_multiple_trials(results_dir, est_type, n_trials,
                            recalculate_errors=False,
                            preset_boxplot_distances=[],
                            preset_boxplot_percentages=[0.1, 0.2, 0.3, 0.4, 0.5],
                            compute_odometry_error=True,
                            nm_gt=None, nm_est=None, data_dir=None):
    traj_list = []
    mt_error = MulTrajError()
    if nm_gt is None:
        nm_gt = 'stamped_groundtruth.txt'
    if nm_est is not None and n_trials != 1:
        raise ValueError("An explicit estimate file requires n_trials == 1.")

    for trial_i in range(n_trials):
        if n_trials == 1:
            suffix = ''
        else:
            suffix = str(trial_i)
        print(Fore.RED+"### Trial {0} ###".format(trial_i))

        match_base_fn = match_filename_prefix(est_type) + suffix + '.' + kFnExt
        if nm_est is None:
            cur_nm_est = kNsToEstFnMapping[est_type] + suffix + '.' + kFnExt
        else:
            cur_nm_est = nm_est

        if recalculate_errors:
            Trajectory.remove_cached_error(results_dir,
                                           est_type, suffix)
            Trajectory.remove_files_in_save_dir(results_dir, est_type,
                                                match_base_fn)
        traj = Trajectory(
            results_dir, est_type=est_type, suffix=suffix,
            nm_gt=nm_gt,
            nm_est=cur_nm_est,
            nm_matches=match_base_fn,
            preset_boxplot_distances=preset_boxplot_distances,
            preset_boxplot_percentages=preset_boxplot_percentages,
            data_dir=data_dir)
        if traj.data_loaded:
            traj.compute_absolute_error()
            if compute_odometry_error:
                traj.compute_relative_errors()
        if traj.success:
            traj.cache_current_error()
            traj.write_errors_to_yaml()

        if traj.success and not preset_boxplot_distances:
            print("Save the boxplot distances for next trials.")
            preset_boxplot_distances = traj.preset_boxplot_distances

        if traj.success:
            mt_error.addTrajectoryError(traj, trial_i)
            traj_list.append(traj)
        else:
            print("Trials {0} fails, will not count.".format(trial_i))
    mt_error.summary()
    mt_error.updateStatistics()
    return traj_list, mt_error


def _expected_est_paths(est_type, resolved, n_trials):
    """Return the estimate file paths expected for the report."""
    if resolved.est_path:
        return [resolved.est_path]
    base_name = kNsToEstFnMapping[est_type]
    if n_trials == 1:
        return [os.path.join(resolved.data_dir, base_name + '.' + kFnExt)]
    return [
        os.path.join(resolved.data_dir,
                     base_name + str(trial_i) + '.' + kFnExt)
        for trial_i in range(n_trials)
    ]


def _build_report_entry(est_type, resolved, traj_list, mt_error,
                        n_trials, output_dir):
    """Collect primitives for the Markdown report."""
    entry = {
        'est_type': est_type,
        'gt_path': resolved.gt_path,
        'est_paths': _expected_est_paths(est_type, resolved, n_trials),
        'input_dir': resolved.data_dir,
        'output_dir': output_dir,
        'align_type': None,
        'align_num_frames': None,
        'n_trials': n_trials,
        'success_indices': list(mt_error.success_indices),
        'success': bool(traj_list),
        'plots': [],
    }
    if not traj_list:
        entry['failure_reason'] = (
            '未能成功加载、匹配或对齐轨迹。请检查轨迹格式、时间戳，'
            '以及真值轨迹和对比轨迹是否对应。')
        return entry

    first = traj_list[0]
    entry['align_type'] = first.align_type
    entry['align_num_frames'] = first.align_num_frames

    trial_stats = []
    for trial_i, traj in enumerate(traj_list):
        original_index = (
            mt_error.success_indices[trial_i]
            if trial_i < len(mt_error.success_indices) else trial_i)
        gt_length = float(traj.traj_length)
        try:
            est_length = float(
                traj_utils.get_distance_from_start(traj.p_es_aligned)[-1])
        except (IndexError, TypeError, ValueError):
            est_length = 0.0
        if gt_length > 0.0:
            length_diff_perc = (est_length - gt_length) / gt_length * 100.0
        else:
            length_diff_perc = None
        if len(traj.abs_errors.get('abs_e_trans_vec', [])) > 0:
            end_error = float(np.linalg.norm(
                traj.abs_errors['abs_e_trans_vec'][-1]))
        else:
            end_error = None
        trial_stats.append({
            'index': original_index,
            'num_matches': int(len(traj.t_gt)),
            'gt_length': gt_length,
            'est_length': est_length,
            'length_diff_perc': length_diff_perc,
            'end_error': end_error,
            'scale': float(traj.scale),
            'time_start': float(traj.t_es[0]) if len(traj.t_es) else None,
            'time_end': float(traj.t_es[-1]) if len(traj.t_es) else None,
            'trans_rmse': float(traj.abs_errors['abs_e_trans_stats']['rmse']),
            'rot_rmse': float(traj.abs_errors['abs_e_rot_stats']['rmse']),
            'scale_rmse': float(traj.abs_errors['abs_e_scale_stats']['rmse']),
        })
    entry['trial_stats'] = trial_stats

    if n_trials == 1:
        entry['abs_stats'] = {
            'trans': first.abs_errors['abs_e_trans_stats'],
            'rot': first.abs_errors['abs_e_rot_stats'],
            'scale': first.abs_errors['abs_e_scale_stats'],
        }
    else:
        entry['abs_stats'] = {
            'trans': mt_error.abs_errors['rmse_trans_stats'],
            'rot': mt_error.abs_errors['rmse_rot_stats'],
            'scale': mt_error.abs_errors['rmse_scale_stats'],
        }

    rel_stats = {}
    for distance, errors in mt_error.rel_errors.items():
        rel_stats[distance] = {
            'trans': errors.get('rel_trans_stats'),
            'trans_perc': errors.get('rel_trans_perc_stats'),
            'yaw': errors.get('rel_yaw_stats'),
            'rot_deg_per_m': errors.get('rel_rot_deg_per_m_stats'),
        }
    entry['rel_stats'] = rel_stats
    return entry


def _validate_args(args):
    """Validate argument combinations and return the mode flags."""
    if args.mul_trials is not None and args.mul_trials < 1:
        raise InputResolutionError("--mul_trials 必须是正整数。")

    est_types_explicit = args.est_types is not None
    if est_types_explicit and not args.est_types:
        raise InputResolutionError("--est_types 至少需要指定一种估计类型。")
    if est_types_explicit:
        for est_type in args.est_types:
            if est_type not in kNsToEstFnMapping or \
                    est_type not in kNsToMatchFnMapping:
                raise InputResolutionError(
                    "未知的估计类型：{0}".format(est_type))

    legacy_mode = est_types_explicit or (
        args.mul_trials is not None and args.mul_trials > 1)

    input_is_file = os.path.isfile(args.input_path)
    input_is_dir = os.path.isdir(args.input_path)
    if not input_is_file and not input_is_dir:
        raise InputResolutionError(
            "输入路径不存在或不是文件夹/文件：{0}".format(args.input_path))

    if input_is_file:
        if legacy_mode:
            raise InputResolutionError(
                "显式轨迹文件输入不能与 --est_types 或 --mul_trials > 1 同时使用。")
        if not args.comparison_path:
            raise InputResolutionError(
                "第一个参数是轨迹文件时，必须提供对比轨迹文件路径。")
    elif args.comparison_path and legacy_mode:
        raise InputResolutionError(
            "文件夹输入 + 显式对比轨迹时不能使用 --est_types 或 "
            "--mul_trials > 1。")
    return legacy_mode


def main(argv=None):
    global FORMAT
    parser = argparse.ArgumentParser(
        description='''Analyze trajectory estimate in a folder.''')
    parser.add_argument(
        'input_path', type=str,
        help="结果文件夹，或真值轨迹文件（.txt）。")
    parser.add_argument(
        'comparison_path', type=str, nargs='?', default=None,
        help="对比轨迹文件；第一个参数为文件时必填，为文件夹时可覆盖自动选择。")
    parser.add_argument(
        '--output_dir', type=str, default=None,
        help="saved_results 和 plots 的输出目录。默认：文件夹输入时为该文件夹，"
             "文件输入时为对比轨迹所在目录。")
    parser.add_argument(
        '--plots_dir', type=str,
        help="Folder to output plots",
        default='')
    parser.add_argument(
        '--mul_trials', type=int,
        help='number of trials, None for single run', default=None)
    parser.add_argument(
        '--mul_plot_idx', type=int,
        nargs="*",
        help='index of  trials for plotting', default=[0])
    parser.add_argument(
        '--est_types', '--est_type', dest='est_types',
        nargs="*", type=str, default=None,
        help='传统模式：按 fn_constants 映射分析这些估计类型；省略时自动识别。')
    parser.add_argument('--recalculate_errors',
                        help='Deletes cached errors', action='store_true')
    parser.add_argument('--png',
                        help='Save plots as png (default)',
                        action='store_true')
    parser.add_argument('--pdf',
                        help='Save plots as pdf instead of png',
                        action='store_true')
    parser.add_argument('--plot_scale_traj',
                        help='whether to plot scale colored trajectory (slow)',
                        action='store_true')
    parser.add_argument('--plot', dest='plot',
                        action='store_true')
    parser.add_argument('--no_plot', dest='plot',
                        action='store_false')
    parser.set_defaults(plot=True)
    args = parser.parse_args(argv)

    try:
        legacy_mode = _validate_args(args)
        resolved = resolve_inputs(
            args.input_path,
            comparison_path=args.comparison_path,
            output_dir=args.output_dir,
            resolve_comparison=not legacy_mode)
    except InputResolutionError as e:
        print(Fore.RED + "[错误] {0}".format(e), file=sys.stderr)
        return 1

    output_dir = resolved.output_dir
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        print(Fore.RED + "[错误] 无法创建输出目录 {0}: {1}".format(
            output_dir, e), file=sys.stderr)
        return 1

    if legacy_mode:
        n_trials = args.mul_trials or 1
        est_types = args.est_types or ['traj_est']
    else:
        n_trials = 1
        est_types = [resolved.est_label]

    top_plots_dir = args.plots_dir
    if not args.plots_dir:
        top_plots_dir = os.path.join(output_dir, 'plots')
    top_plots_dir = os.path.abspath(top_plots_dir)
    if not os.path.exists(top_plots_dir):
        os.makedirs(top_plots_dir)

    plots_dirs = []
    for est_type in est_types:
        plot_dir_i = os.path.join(top_plots_dir, est_type)
        if not os.path.exists(plot_dir_i):
            os.makedirs(plot_dir_i)
        plots_dirs.append(plot_dir_i)
    FORMAT = '.pdf' if args.pdf else '.png'

    print(Fore.YELLOW + "=== 评估输入 ===")
    print("真值轨迹：{0}".format(resolved.gt_path))
    if resolved.est_path:
        print("对比轨迹：{0}".format(resolved.est_path))
    print("输入目录：{0}".format(resolved.data_dir))
    print("输出目录：{0}".format(output_dir))
    print("估计类型：{0}".format(est_types))
    print("绘图目录：{0}".format(plots_dirs))
    report_path = os.path.join(
        output_dir, Trajectory.saved_res_dir_nm, RESULT_REPORT_FILENAME)
    print("报告路径：{0}".format(report_path))

    print(Fore.YELLOW + "=== Summary ===")
    if args.mul_trials:
        print(Fore.YELLOW +
              "We will ananlyze multiple trials #{0}".format(args.mul_trials))
        if len(args.mul_plot_idx) == 0:
            args.mul_plot_idx = (np.arange(args.mul_trials)).tolist()
        print(Fore.YELLOW +
              "We will plot trials {0}.".format(args.mul_plot_idx))
    else:
        args.mul_plot_idx = [0]
    assert len(args.mul_plot_idx) == 1, "Multiple plots not supported yet"

    report_entries = []
    any_success = False
    for est_type_i, plot_dir_i in zip(est_types, plots_dirs):
        print(Fore.RED +
              "#### Processing error type {0} ####".format(est_type_i))
        mt_error = MulTrajError()
        nm_est = resolved.est_path if not legacy_mode else None
        traj_list, mt_error = analyze_multiple_trials(
            output_dir, est_type_i, n_trials,
            recalculate_errors=args.recalculate_errors,
            nm_gt=resolved.gt_path, nm_est=nm_est,
            data_dir=resolved.data_dir)

        entry = _build_report_entry(
            est_type_i, resolved, traj_list, mt_error,
            n_trials, output_dir)
        saved_plot_files = []
        any_success = any_success or bool(traj_list)

        if n_trials > 1:
            print(">>> Save results for multiple runs in {0}...".format(
                mt_error.save_results_dir))
            mt_error.saveErrors()
            mt_error.cache_current_error()

        if not args.plot:
            print("#### Skip plotting and go to next error type.")
            report_entries.append(entry)
            continue

        if not traj_list:
            print("No success runs, not plotting.")
            report_entries.append(entry)
            continue

        plot_index = args.mul_plot_idx[0]
        if plot_index >= len(traj_list):
            print(Fore.YELLOW + "Plot index {0} is out of range, use 0.".format(
                plot_index))
            plot_index = 0
        plot_traj = traj_list[plot_index]

        def _save_plot(fig, filename):
            save_figure(fig, filename)
            saved_plot_files.append(os.path.abspath(filename))

        print(Fore.MAGENTA +
              ">>> Plotting absolute error for one trajectory...")
        fig = plt.figure(figsize=(6, 5.5))
        ax = fig.add_subplot(111, aspect='equal',
                             xlabel='x [m]', ylabel='y [m]')
        pu.plot_trajectory_top(ax, plot_traj.p_es_aligned, 'b', 'Estimate')
        pu.plot_trajectory_top(ax, plot_traj.p_gt, 'm', 'Groundtruth')
        pu.plot_aligned_top(ax, plot_traj.p_es_aligned, plot_traj.p_gt,
                            plot_traj.align_num_frames)
        plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        fig.tight_layout()
        _save_plot(fig, plot_dir_i+'/trajectory_top' + '_' +
                   plot_traj.align_str + FORMAT)

        fig = plt.figure(figsize=(6, 5.5))
        ax = fig.add_subplot(111, aspect='equal',
                             xlabel='x [m]', ylabel='z [m]')
        pu.plot_trajectory_side(ax, plot_traj.p_es_aligned, 'b', 'Estimate')
        pu.plot_trajectory_side(ax, plot_traj.p_gt, 'm', 'Groundtruth')
        plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        fig.tight_layout()
        _save_plot(fig, plot_dir_i+'/trajectory_side' + '_' +
                   plot_traj.align_str + FORMAT)

        # 3D groundtruth trajectory.
        fig = plt.figure(figsize=(7, 6))
        ax = fig.add_subplot(111, projection='3d',
                             xlabel='x [m]', ylabel='y [m]', zlabel='z [m]')
        pu.plot_trajectory_3d(ax, plot_traj.p_gt, 'm', 'Groundtruth')
        pu.set_3d_axes_equal(ax, [plot_traj.p_gt])
        ax.legend()
        fig.tight_layout()
        _save_plot(fig, plot_dir_i+'/trajectory_3d_gt' + '_' +
                   plot_traj.align_str + FORMAT)

        # 3D comparison of the aligned estimate and the groundtruth.
        fig = plt.figure(figsize=(7, 6))
        ax = fig.add_subplot(111, projection='3d',
                             xlabel='x [m]', ylabel='y [m]', zlabel='z [m]')
        pu.plot_trajectory_3d(ax, plot_traj.p_es_aligned, 'b', 'Estimate')
        pu.plot_trajectory_3d(ax, plot_traj.p_gt, 'm', 'Groundtruth')
        pu.set_3d_axes_equal(
            ax, [plot_traj.p_es_aligned, plot_traj.p_gt])
        ax.legend()
        fig.tight_layout()
        _save_plot(fig, plot_dir_i+'/trajectory_3d' + '_' +
                   plot_traj.align_str + FORMAT)

        fig = plt.figure(figsize=(8, 2.5))
        ax = fig.add_subplot(
            111, xlabel='Distance [m]', ylabel='Position Drift [mm]',
            xlim=[0, plot_traj.accum_distances[-1]])
        pu.plot_error_n_dim(ax, plot_traj.accum_distances,
                            plot_traj.abs_errors['abs_e_trans_vec']*1000,
                            plot_dir_i)
        ax.legend()
        fig.tight_layout()
        _save_plot(fig, plot_dir_i+'/translation_error' + '_' +
                   plot_traj.align_str + FORMAT)

        fig = plt.figure(figsize=(8, 2.5))
        ax = fig.add_subplot(
            111, xlabel='Distance [m]', ylabel='Orient. err. [deg]',
            xlim=[0, plot_traj.accum_distances[-1]])
        pu.plot_error_n_dim(
            ax, plot_traj.accum_distances,
            plot_traj.abs_errors['abs_e_ypr']*180.0/np.pi, plot_dir_i,
            labels=['yaw', 'pitch', 'roll'])
        ax.legend()
        fig.tight_layout()
        _save_plot(fig, plot_dir_i+'/rotation_error'+'_' +
                   plot_traj.align_str + FORMAT)

        fig = plt.figure(figsize=(8, 2.5))
        ax = fig.add_subplot(
            111, xlabel='Distance [m]', ylabel=r'Scale Drift [\%]',
            xlim=[0, plot_traj.accum_distances[-1]])
        pu.plot_error_n_dim(
            ax, plot_traj.accum_distances,
            np.reshape(plot_traj.abs_errors['abs_e_scale_perc'], (-1, 1)),
            plot_dir_i, colors=['b'], labels=['scale'])
        ax.legend()
        fig.tight_layout()
        _save_plot(fig, plot_dir_i+'/scale_error'+'_' +
                   plot_traj.align_str+FORMAT)

        if args.plot_scale_traj:
            fig = plt.figure(figsize=(6, 12))
            ax_top = fig.add_subplot(211, aspect='equal',
                                     xlabel='x [m]', ylabel='y [m]',
                                     title='Top')
            ax_top.grid(ls='--', color='0.7')
            ax_side = fig.add_subplot(212, aspect='equal',
                                      xlabel='x [m]', ylabel='z [m]',
                                      title='Side')
            ax_side.grid(ls='--', color='0.7')
            abs_scale_e = np.abs(
                np.reshape(plot_traj.abs_errors['abs_e_scale_perc'], (-1, 1)),)
            color_idx =\
                (abs_scale_e-np.min(abs_scale_e))/(
                    np.max(abs_scale_e)-np.min(abs_scale_e))
            for idx, val in enumerate(color_idx[:-1]):
                c = matplotlib.cm.jet(val).flatten()
                ax_top.plot(plot_traj.p_gt[idx:idx+2, 0],
                            plot_traj.p_gt[idx:idx+2, 1], color=c)
                ax_side.plot(plot_traj.p_gt[idx:idx+2, 0],
                             plot_traj.p_gt[idx:idx+2, 2], color=c)
            fig.tight_layout()
            _save_plot(fig, plot_dir_i+'/scale_error_traj' + '_' +
                       plot_traj.align_str + FORMAT)

        print(Fore.MAGENTA+">>> Plotting relative (odometry) error...")
        suffix = ''
        if n_trials > 1:
            suffix = '_mt'

        plot_types = ['rel_trans', 'rel_trans_perc', 'rel_yaw']
        rel_errors, distances = mt_error.get_relative_errors_and_distances(
            error_types=plot_types)

        labels = ['Estimate']
        colors = ['b']

        fig = plt.figure(figsize=(6, 2.5))
        ax = fig.add_subplot(
            111, xlabel='Distance traveled [m]',
            ylabel='Translation error [m]')
        pu.boxplot_compare(ax, distances, rel_errors['rel_trans'],
                           labels, colors)
        fig.tight_layout()
        _save_plot(fig, plot_dir_i+'/rel_translation_error' + suffix +
                   FORMAT)
        plt.close(fig)

        fig = plt.figure(figsize=(6, 2.5))
        ax = fig.add_subplot(
            111, xlabel='Distance traveled [m]',
            ylabel=r'Translation error [\%]')
        pu.boxplot_compare(
            ax, distances, rel_errors['rel_trans_perc'], labels, colors)
        fig.tight_layout()
        _save_plot(fig, plot_dir_i+'/rel_translation_error_perc'+suffix +
                   FORMAT)
        plt.close(fig)

        fig = plt.figure(figsize=(6, 2.5))
        ax = fig.add_subplot(
            111, xlabel='Distance traveled [m]',
            ylabel='Yaw error [deg]')
        pu.boxplot_compare(ax, distances, rel_errors['rel_yaw'],
                           labels, colors)
        fig.tight_layout()
        _save_plot(fig, plot_dir_i+'/rel_yaw_error' + suffix + FORMAT)
        plt.close(fig)

        entry['plots'] = saved_plot_files
        report_entries.append(entry)
        print(Fore.GREEN +
              "#### Done processing error type {0} ####".format(est_type_i))

    try:
        write_markdown_report(report_path, report_entries)
    except OSError as e:
        print(Fore.RED + "[错误] 无法写入报告 {0}: {1}".format(
            report_path, e), file=sys.stderr)
        return 1
    print(Fore.GREEN + "评估报告已保存到 {0}".format(report_path))

    if shutil.which('notify-send'):
        import subprocess as s
        s.call(['notify-send', 'rpg_trajectory_evaluation finished',
                'results in: {0}\nreport: {1}'.format(
                    os.path.abspath(output_dir),
                    os.path.abspath(report_path))])
    return 0 if any_success else 1


if __name__ == '__main__':
    sys.exit(main())
