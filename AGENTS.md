# Repository Guidelines

## 项目结构

- `ros2_ws/src/rpg_trajectory_evaluation/` 是 ROS 2 `ament_python` 包：
  - `rpg_trajectory_evaluation/` 包含轨迹加载、时间戳匹配、轨迹对齐、绝对与相对误差计算、绘图和结果写入模块；
  - `rpg_trajectory_evaluation/cli/` 包含单次/批量评估入口，`rpg_trajectory_evaluation/cli/dataset_tools/` 提供位姿格式转换工具；
  - `rpg_trajectory_evaluation/fn_constants.py` 定义估计类型与文件名的对应关系；
  - `test/` 包含 pytest 测试，`resource/`、`package.xml`、`setup.py`、`setup.cfg` 是 ROS 2 包元数据。
- `analyze_trajectories_config/` 存放批量评估的 YAML 配置示例，`results/` 存放 EuRoC 示例数据，`doc/` 存放 README 使用的图片。
- 仓库根目录的 `pyproject.toml`、`.python-version`、`uv.lock` 定义 uv 开发环境，`.venv` 创建在仓库根目录，不参与 ROS 2 构建。

## 构建与运行

使用 Python 3（>=3.10，uv 虚拟环境固定 3.12）与 ROS 2 Jazzy。

uv 开发环境：

```bash
uv sync
uv run pytest
uv run analyze_trajectory_single <result_dir> --no_plot --recalculate_errors
```

ROS 2 构建（`build/`、`install/`、`log/` 全部位于 `ros2_ws/` 下）：

```bash
source /opt/ros/jazzy/setup.bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 run rpg_trajectory_evaluation analyze_trajectory_single <result_dir> --no_plot --recalculate_errors
```

从仓库根目录运行批量评估：

```bash
uv run analyze_trajectories analyze_trajectories_config/euroc_vislam_mono.yaml \
  --results_dir=./results/euroc_vislam_mono \
  --output_dir=./results/euroc_vislam_mono --platform laptop
```

输入目录需包含 `stamped_groundtruth.txt` 和 `stamped_traj_estimate.txt`。位姿记录的时间戳以秒为单位，四元数按 `qx qy qz qw` 排列。批量评估的配置、输入和输出选项可通过 `uv run analyze_trajectories --help` 查看。

`ros2 run` 使用系统 Python，依赖由 `package.xml`/rosdep 提供（`rosdep install --from-paths ros2_ws/src --ignore-src -r -y`）。uv 环境用于独立运行 CLI 和测试；`bag_to_pose` 需要先 source ROS 2 环境。

## 代码风格

每级缩进使用四个空格。新模块、函数和变量使用 `snake_case`，类名使用 `PascalCase`。保留已有公共接口名称（`Trajectory` 类及其方法）和结果文件格式（`saved_results/` 下的 YAML 文件名与统计字段）。代码需兼容 Python 3。仓库未配置格式化或静态检查工具。

## 测试与验证

使用 pytest，测试位于 `ros2_ws/src/rpg_trajectory_evaluation/test/`，使用合成数据做冒烟测试：

```bash
uv run pytest
```

修改评估逻辑后，还应将自带的 EuRoC 示例（如 `laptop_vio_mono_MH_05`）复制到可写目录，运行单次评估并检查 `saved_results/` 中的 YAML 统计值与基线一致。验证绘图变更时去掉 `--no_plot` 并检查生成的图表。提交时排除 `.venv`、`ros2_ws/build|install|log`、`saved_results`、`__pycache__` 等生成物。

## 提交与拉取请求

近期提交多使用简短、直接的标题，例如 `fix yaml loading and default percentages`。每个提交聚焦一项改动，标题写明变化。提交拉取请求时，说明改动内容，关联相关 Issue，并附上验证所用的数据集、命令和实际结果。涉及图表变化时，附上修改前后的对比图。
