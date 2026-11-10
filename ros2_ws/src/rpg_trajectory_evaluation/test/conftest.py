import os
import tempfile

# Must be set before matplotlib is imported anywhere.  The plotting code falls
# back to mathtext when LaTeX is unavailable, and Agg works headless.
os.environ.setdefault('MPLBACKEND', 'Agg')
if 'MPLCONFIGDIR' not in os.environ:
    os.environ['MPLCONFIGDIR'] = tempfile.mkdtemp(prefix='rpg_traj_mpl_')

import numpy as np
import pytest


def _write_poses(path, timestamps, positions, quaternions):
    data = np.column_stack([timestamps, positions, quaternions])
    np.savetxt(str(path), data, fmt='%.12f')


@pytest.fixture
def synthetic_dataset(tmp_path):
    """Create a small synthetic groundtruth/estimate dataset."""
    n_frames = 300
    dt = 0.01
    radius = 5.0
    timestamps = np.arange(n_frames) * dt
    angles = 2.0 * np.pi * np.arange(n_frames) / (1.5 * n_frames)
    p_gt = np.column_stack([
        radius * np.cos(angles),
        radius * np.sin(angles),
        np.zeros(n_frames),
    ])
    q_gt = np.tile(np.array([0.0, 0.0, 0.0, 1.0]), (n_frames, 1))

    p_es = p_gt + 1e-3 * np.column_stack([
        np.sin(3.0 * angles),
        np.cos(2.0 * angles),
        np.zeros(n_frames),
    ])
    q_es = q_gt.copy()

    _write_poses(tmp_path / 'stamped_groundtruth.txt',
                 timestamps, p_gt, q_gt)
    _write_poses(tmp_path / 'stamped_traj_estimate.txt',
                 timestamps, p_es, q_es)
    (tmp_path / 'eval_cfg.yaml').write_text(
        'align_type: posyaw\nalign_num_frames: -1\n')
    return tmp_path
