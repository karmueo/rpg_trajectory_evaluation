#!/usr/bin/env python3
"""
@author: Christian Forster
"""

import shutil

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import rc

FORMAT = '.pdf'

# Light yellow used for the groundtruth trajectory in all trajectory plots.
GROUNDTRUTH_COLOR = '#FFEB3B'
# Trajectory lines are drawn semi-transparent; start/end markers stay opaque.
TRAJECTORY_LINE_ALPHA = 0.7


def configure_matplotlib(use_tex=None):
    """Configure matplotlib for the trajectory evaluation plots.

    LaTeX rendering is only enabled when both ``latex`` and ``dvipng`` are
    available.  On machines without a LaTeX installation matplotlib's
    built-in mathtext is used instead so that plotting still works.
    """
    if use_tex is None:
        use_tex = bool(shutil.which('latex') and shutil.which('dvipng'))
    rc('font', **{'family': 'serif', 'serif': ['Cardo', 'DejaVu Serif']})
    rc('text', usetex=use_tex)
    return use_tex


configure_matplotlib()


def color_box(bp, color):
    elements = ['medians', 'boxes', 'caps', 'whiskers']
    # Iterate over each of the elements changing the color
    for elem in elements:
        [plt.setp(bp[elem][idx], color=color, linestyle='-', lw=1.0)
         for idx in range(len(bp[elem]))]
    return


def boxplot_compare(ax, xlabels,
                    data, data_labels, data_colors,
                    legend=True):
    n_data = len(data)
    n_xlabel = len(xlabels)
    leg_handles = []
    leg_labels = []
    idx = 0
    for idx, d in enumerate(data):
        # print("idx and d: {0} and {1}".format(idx, d))
        w = 1 / (1.5 * n_data + 1.5)
        widths = [w for pos in np.arange(n_xlabel)]
        positions = [pos - 0.5 + 1.5 * w + idx * w
                     for pos in np.arange(n_xlabel)]
        # print("Positions: {0}".format(positions))
        bp = ax.boxplot(d, positions=positions, widths=widths,
                        notch=0, sym='')
        color_box(bp, data_colors[idx])
        tmp, = plt.plot([1, 1], c=data_colors[idx], alpha=0)
        leg_handles.append(tmp)
        leg_labels.append(data_labels[idx])
        idx += 1

    ax.set_xticks(np.arange(n_xlabel))
    ax.set_xticklabels(xlabels)
    xlims = ax.get_xlim()
    ax.set_xlim([xlims[0]-0.1, xlims[1]-0.1])
    if legend:
        # ax.legend(leg_handles, leg_labels, bbox_to_anchor=(
            # 1.05, 1), loc=2, borderaxespad=0.)
        ax.legend(leg_handles, leg_labels)


def plot_start_end_markers(ax, xs, ys, color, zs=None):
    """Mark the start (small filled circle) and end (cross) of a curve.

    The markers are always fully opaque, independent of the line opacity.
    """
    if len(xs) == 0:
        return
    start_style = dict(linestyle='None', markersize=5, color=color, zorder=5)
    end_style = dict(linestyle='None', markersize=6, color=color,
                     markeredgewidth=1.2, zorder=5)
    if zs is None:
        ax.plot([xs[0]], [ys[0]], marker='o', **start_style)
        ax.plot([xs[-1]], [ys[-1]], marker='x', **end_style)
    else:
        ax.plot([xs[0]], [ys[0]], [zs[0]], marker='o', **start_style)
        ax.plot([xs[-1]], [ys[-1]], [zs[-1]], marker='x', **end_style)


def plot_trajectory_top(ax, pos, color, name, alpha=1.0):
    ax.grid(ls='--', color='0.7')
    # pos_0 = pos - pos[0, :]
    ax.plot(pos[:, 0], pos[:, 1], color, linestyle='-', alpha=alpha, label=name)
    plot_start_end_markers(ax, pos[:, 0], pos[:, 1], color)


def plot_trajectory_side(ax, pos, color, name, alpha=1.0):
    ax.grid(ls='--', color='0.7')
    # pos_0 = pos - pos[0, :]
    ax.plot(pos[:, 0], pos[:, 2], color, linestyle='-', alpha=alpha, label=name)
    plot_start_end_markers(ax, pos[:, 0], pos[:, 2], color)


def plot_trajectory_3d(ax, pos, color, name, alpha=1.0):
    ax.grid(ls='--', color='0.7')
    ax.plot(pos[:, 0], pos[:, 1], pos[:, 2], color,
            linestyle='-', alpha=alpha, label=name)
    plot_start_end_markers(ax, pos[:, 0], pos[:, 1], color,
                           zs=pos[:, 2])


def set_3d_axes_equal(ax, positions):
    """Use the same metric scale on the three axes of a 3D plot."""
    all_pos = np.vstack(positions)
    mins = np.min(all_pos, axis=0)
    maxs = np.max(all_pos, axis=0)
    center = (mins + maxs) / 2.0
    half_range = np.max(maxs - mins) / 2.0
    if half_range <= 0.0:
        half_range = 1.0
    # A small margin keeps the trajectory from touching the axes.
    half_range *= 1.05
    ax.set_xlim(center[0] - half_range, center[0] + half_range)
    ax.set_ylim(center[1] - half_range, center[1] + half_range)
    ax.set_zlim(center[2] - half_range, center[2] + half_range)
    ax.set_box_aspect((1, 1, 1))


def plot_aligned_top(ax, p_gt, p_es, n_align_frames):
    if n_align_frames <= 0:
        n_align_frames = p_es.shape[0]
    # p_es_0 = p_es - p_gt[0, :]
    # p_gt_0 = p_gt - p_gt[0, :]
    # ax.plot(p_es[0:n_align_frames, 0], p_es[0:n_align_frames, 1],
        # 'g-', linewidth=2, label='aligned')
    for (x1, y1, z1), (x2, y2, z2) in zip(
            p_es[:n_align_frames:10, :], p_gt[:n_align_frames:10, :]):
        ax.plot([x1, x2], [y1, y2], '-', color="gray")


def plot_error_n_dim(ax, distances, errors, results_dir,
                     colors=['r', 'g', 'b'],
                     labels=['x', 'y', 'z']):
    assert len(colors) == len(labels)
    assert len(colors) == errors.shape[1]
    for i in range(len(colors)):
        ax.plot(distances, errors[:, i],
                colors[i]+'-', label=labels[i])
