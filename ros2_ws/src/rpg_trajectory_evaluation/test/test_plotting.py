import numpy as np
from matplotlib import pyplot as plt

from rpg_trajectory_evaluation import plot_utils
from rpg_trajectory_evaluation.cli.analyze_trajectory_single import main


def test_single_trajectory_cli_writes_plots(synthetic_dataset):
    assert main([str(synthetic_dataset), '--recalculate_errors']) == 0

    plot_dir = synthetic_dataset / 'plots' / 'traj_est'
    plots = sorted(plot_dir.glob('*.png'))
    assert len(plots) >= 7
    assert all(p.stat().st_size > 0 for p in plots)
    names = [p.name for p in plots]
    assert any(n.startswith('trajectory_3d_gt_') for n in names)
    assert any(n.startswith('trajectory_3d_est_') for n in names)
    assert any(n.startswith('trajectory_3d_') and
               not n.startswith('trajectory_3d_gt_') and
               not n.startswith('trajectory_3d_est_') for n in names)
    assert not list(plot_dir.glob('*.pdf'))

    report = synthetic_dataset / 'saved_results' / 'result.md'
    assert report.is_file()
    text = report.read_text(encoding='utf-8')
    assert '![轨迹俯视图](<../plots/traj_est/trajectory_top_' in text
    for plot in plots:
        assert plot.name in text


def test_trajectory_helpers_mark_start_and_end():
    pos = np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0], [2.0, 4.0, 6.0]])
    fig = plt.figure()
    ax_top = fig.add_subplot(121)
    ax_3d = fig.add_subplot(122, projection='3d')
    plot_utils.plot_trajectory_top(ax_top, pos, 'b', 'Estimate',
                                   plot_utils.TRAJECTORY_LINE_ALPHA)
    plot_utils.plot_trajectory_3d(
        ax_3d, pos, plot_utils.GROUNDTRUTH_COLOR, 'Groundtruth')

    for ax, expected_alpha in (
            (ax_top, plot_utils.TRAJECTORY_LINE_ALPHA), (ax_3d, 1.0)):
        markers = [line for line in ax.get_lines()
                   if line.get_linestyle() == 'None']
        assert sum(line.get_marker() == 'o' for line in markers) == 1
        assert sum(line.get_marker() == 'x' for line in markers) == 1
        start = next(line for line in markers if line.get_marker() == 'o')
        end = next(line for line in markers if line.get_marker() == 'x')
        assert start.get_xdata()[0] == pos[0, 0]
        assert start.get_ydata()[0] == pos[0, 1]
        assert end.get_xdata()[0] == pos[-1, 0]
        assert end.get_ydata()[0] == pos[-1, 1]
        assert start.get_alpha() in (None, 1.0)
        assert end.get_alpha() in (None, 1.0)
        line = next(line for line in ax.get_lines()
                    if line.get_linestyle() == '-')
        assert line.get_alpha() == expected_alpha
    plt.close(fig)
