from rpg_trajectory_evaluation.cli.analyze_trajectory_single import main


def test_single_trajectory_cli_writes_plots(synthetic_dataset):
    assert main([str(synthetic_dataset), '--recalculate_errors']) == 0

    plot_dir = synthetic_dataset / 'plots' / 'traj_est'
    plots = sorted(plot_dir.glob('*.png'))
    assert len(plots) >= 7
    assert all(p.stat().st_size > 0 for p in plots)
    names = [p.name for p in plots]
    assert any(n.startswith('trajectory_3d_gt_') for n in names)
    assert any(n.startswith('trajectory_3d_') and
               not n.startswith('trajectory_3d_gt_') for n in names)
    assert not list(plot_dir.glob('*.pdf'))

    report = synthetic_dataset / 'saved_results' / 'result.md'
    assert report.is_file()
    text = report.read_text(encoding='utf-8')
    assert '![轨迹俯视图](<../plots/traj_est/trajectory_top_' in text
    for plot in plots:
        assert plot.name in text
