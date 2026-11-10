# rpg_trajectory_evaluation

本仓库实现了视觉（惯性）里程计中常用的轨迹评估方法。具体包括：

* 多种轨迹对齐方式（刚体变换、相似变换和仅偏航角旋转）
* 常用误差指标：绝对轨迹误差（ATE）和相对/里程计误差（RE）

> 相对误差的实现方式与 [KITTI](http://www.cvlibs.net/publications/Geiger2012CVPR.pdf) 一致，因为这是使用最广泛的版本。

由于轨迹评估涉及很多细节，本工具箱以易用为目标设计。
它既可用于分析[单条轨迹估计](#单条轨迹估计)，也可以用一条命令[在多个数据集上对比不同算法](#多条轨迹估计)（例如[这篇论文](http://rpg.ifi.uzh.ch/docs/ICRA18_Delmerico.pdf)，以及 [IROS 2019 VIO 竞赛](http://rpg.ifi.uzh.ch/uzh-fpv.html)中的用法）。
用户只需提供所需格式的真值和估计，并指定轨迹对齐方式。
工具箱会生成（几乎）可直接用于论文的图表和表格。
此外，评估过程可以很方便地[定制](#定制trajectory-类)。

如果你在学术工作中使用本代码，请引用以下论文：

Zichao Zhang, Davide Scaramuzza: A Tutorial on Quantitative Trajectory Evaluation for Visual(-Inertial) Odometry, IEEE/RSJ Int. Conf. Intell. Robot. Syst. (IROS), 2018. [PDF](https://rpg.ifi.uzh.ch/docs/IROS18_Zhang.pdf)

```
@InProceedings{Zhang18iros,
  author = {Zhang, Zichao and Scaramuzza, Davide},
  title = {A Tutorial on Quantitative Trajectory Evaluation for Visual(-Inertial) Odometry},
  booktitle = {IEEE/RSJ Int. Conf. Intell. Robot. Syst. (IROS)},
  year = {2018}
}
```

1. [安装](#安装)
2. [准备数据](#准备数据)
   * [位姿](#位姿)
   * [评估参数](#评估参数)
   * [起始与结束时间](#起始与结束时间)
3. [运行评估](#运行评估)
   * [单条轨迹估计](#单条轨迹估计)
   * [多条轨迹估计](#多条轨迹估计)
4. [工具](#工具)
   * [数据集工具](#数据集工具)
   * [其他脚本](#其他脚本)
5. [定制：`Trajectory` 类](#定制trajectory-类)
6. [致谢与贡献者](#致谢与贡献者)

## 安装
本工具箱使用 Python 3 编写，已在 Ubuntu 24.04 和 ROS 2 Jazzy 上测试。
本包既可以作为 ROS 2 包使用，也可以作为独立 Python 工具使用。

**ROS 2 包**：包源码位于 `ros2_ws/src/rpg_trajectory_evaluation`。在 `ros2_ws` 工作区下用 `colcon` 构建，构建、安装和日志输出都会写入 `ros2_ws/`：

```bash
source /opt/ros/jazzy/setup.bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
```

**独立 Python 环境**：在仓库根目录用 `uv` 创建虚拟环境：

```bash
uv sync
source .venv/bin/activate   # 可选，也可以直接使用 `uv run ...`
```

**依赖**：

* `numpy` 和 `matplotlib`，用于分析与绘图
* `colorama`，用于彩色控制台输出
* `PyYAML`，用于读取 YAML 配置
* 可选：LaTeX（`latex`、`dvipng`），用于 LaTeX 渲染的图表；未安装时会自动回退到 matplotlib 的 mathtext
* ROS 2（`rclpy`、`rosbag2_py`、`rosidl_runtime_py`、`geometry_msgs`）仅 `bag_to_pose` 数据集工具需要；可用 `rosdep install --from-paths ros2_ws/src --ignore-src -r -y` 安装

## 准备数据
每个待评估的轨迹估计（例如视觉惯性里程计算法的输出）都组织为一个独立的文件夹。
每个文件夹至少需要包含两个文本文件，分别给出带时间戳的真值位姿和估计位姿。

* `stamped_groundtruth.txt`：带时间戳的真值位姿
* `stamped_traj_estimate.txt`：带时间戳的估计位姿
* （可选）`eval_cfg.yaml`：指定评估参数
* （可选）`start_end_time.yaml`：指定用于分析的起始和结束时间（单位为秒）


若要分析 `N` 次运行的结果，估计位姿文件应带有 `0` 到 `N-1` 的后缀。
可参见 `results` 下的文件夹示例。
这些文件包含了**复现定量轨迹评估结果所需的全部关键信息**。

#### 位姿
真值（`stamped_groundtruth.txt`）和估计位姿（`stamped_traj_estimate.txt`）采用如下格式指定

```
# timestamp tx ty tz qx qy qz qw
1.403636580013555527e+09 1.258278699999999979e-02 -1.561510199999999963e-03 -4.015300900000000339e-02 -5.131151899999999988e-02 -8.092916900000000080e-01 8.562779200000000248e-04 5.851609599999999523e-01
......
```

注意，文件以空格分隔，四元数的 `w` 分量放在最后。
时间戳的单位为秒，用于建立时间对应关系。

`rpg_trajectory_evaluation/cli/dataset_tools` 下有一些工具，可帮助你把数据格式（EuRoC 风格、ROS 2 bag）转换为上述格式。
详见下文相应小节。

#### 评估参数
目前 `eval_cfg.yaml` 指定两个用于轨迹对齐的参数（用于绝对误差）：
* `align_type`：
  * `sim3`：相似变换（用于纯视觉单目情形）
  * `se3`：刚体变换（用于纯视觉双目情形）
  * `posyaw`：平移加上绕重力方向的旋转（用于视觉惯性情形）
  * `none`：不对轨迹做对齐
* `align_num_frames`：用于轨迹对齐的位姿数量（从开头算起）。`-1` 表示使用全部位姿。

**如果该文件不存在，将使用 `sim3` 和全部位姿进行轨迹对齐。**

#### 起始与结束时间

`start_end_time.yaml` 可以指定以下内容（以真值时间为准）：
* `start_time_sec`：仅使用该时间之后的位姿进行分析
* `end_time_sec`：仅使用该时间之前的位姿进行分析

**如果该文件不存在，将对 `stamped_traj_estimate.txt` 中的所有位姿进行分析。**


## 运行评估
我们可以对单条估计结果进行评估，也可以对多种算法和多个数据集进行评估。

### 单条轨迹估计

作为 ROS 2 包时，运行

```
ros2 run rpg_trajectory_evaluation analyze_trajectory_single <input> [comparison]
```

在 uv 环境下运行时，运行

```
uv run analyze_trajectory_single <input> [comparison]
```

第一个参数可以是结果文件夹，也可以是真值轨迹文件：

```bash
# 结果文件夹：自动识别真值和对比轨迹
uv run analyze_trajectory_single <result_folder>

# 结果文件夹 + 显式指定对比轨迹
uv run analyze_trajectory_single <result_folder> <comparison.txt>

# 显式指定真值轨迹和对比轨迹
uv run analyze_trajectory_single <groundtruth.txt> <comparison.txt>
```

当第一个参数是文件夹时，脚本会扫描该文件夹第一层的 `.txt` 文件，并将第一条非空行至少包含 8 列数值的文件视为轨迹。文件名包含 `groundtruth`、`ground_truth` 或独立的 `gt` 字段（例如 `gt.txt`、`GT.txt`、`stamped_gt.txt`）时视为真值候选，另一条轨迹则作为对比轨迹。如果候选不唯一，脚本会打印编号供你在终端选择。`--output_dir` 控制 `saved_results` 和 `plots` 的输出位置：文件夹输入时默认为该文件夹，显式文件输入时默认为对比轨迹所在目录。

ROS 2 环境下，把命令中的 `uv run analyze_trajectory_single` 替换为 `ros2 run rpg_trajectory_evaluation analyze_trajectory_single` 即可。

`<result_folder>` 应包含上文提到的真值、轨迹估计，以及可选的评估配置。

#### 输出
评估完成后，你会在输出目录下看到：
* `saved_results/<est_type>`：包含各类误差统计的文本文件（默认估计文件名对应 `traj_est`）
  * `absolute_err_statistics_<align_type>_<align_frames>.yaml`：使用指定对齐方式得到的绝对误差统计。
  * `relative_error_statistics_<len>.yaml`：使用长度为 `<len>` 的子轨迹计算得到的相对误差统计。
  * `cached_rel_err.pickle`：由于相对误差计算耗时较多，我们会按不同子轨迹长度缓存相对误差，以便下次直接使用。
* `saved_results/result.md`：中文 Markdown 评估报告，包含输入路径、对齐配置和误差统计表格，以及带注释的图表；每张图都标注标题、坐标系和曲线含义。
* `plots`：绝对误差、相对（里程计）误差以及轨迹的图表。

即使使用 `--no_plot`，报告也会生成，并在图表章节注明本次未生成图表。

对于多次试验，第 `n` 次试验的结果会带有相应后缀，多次试验的统计会汇总到名为 `mt_*` 的文件中。

例如，执行：
```
uv run analyze_trajectory_single results/euroc_mono_stereo/laptop/vio_mono/laptop_vio_mono_MH_05
```
之后，你会在 `plots` 中看到：

![top_traj](./doc/mh05_top_vio_mono.png)
![abs_err](./doc/mh05_trans_err_vio_mono.png)
![rel_traj](./doc/mh05_rel_translation_error.png)

三维轨迹图会分别保存为 `trajectory_3d_gt_<align>.png`（仅真值）和 `trajectory_3d_<align>.png`（真值与对齐后的估计）。

#### 参数
* `--output_dir`：`saved_results` 和 `plots` 的输出目录。默认：文件夹输入时为该文件夹，显式文件输入时为对比轨迹所在目录。
* `--recalculate_errors`：删除上文提到的误差缓存文件并重新计算全部内容。默认：`False`。
* `--png`：将图表保存为 png（默认）。
* `--pdf`：将图表保存为 pdf 而不是 png。默认：`False`
* `--mul_trials`：分析 `n` 次运行。当 `n > 1` 时，估计文件应以数字后缀结尾（例如 `stamped_traj_estimate0.txt`）。默认：`None`。该选项使用传统的 `stamped_*.txt` 命名方式。

#### 进阶：不同的估计类型
有时，SLAM 算法会输出多种类型的轨迹，例如实时位姿和优化后的关键帧位姿（例如位姿图、光束法平差）。通过在命令行末尾指定估计类型，可以让脚本分析不同的文件，例如
* `--est_types traj_est`：分析 `stamped_traj_estimate.txt`
* `--est_types pose_graph`：分析 `stamped_pose_graph_estimate.txt`
* `--est_types traj_est pose_graph`：同时分析两者。此时你可以在 `saved_results` 和 `plots` 下对应的子目录中找到结果。

`--est_type` 可以作为 `--est_types` 的别名。省略 `--est_types` 时，脚本按上文规则自动选择对比轨迹。

`est_type` 到文件名（即 `stamped_*.txt`）的映射定义在 `rpg_trajectory_evaluation/fn_constants.py` 中。该映射同样用于分析多条轨迹。可以在 `results/euroc_vislam_mono` 中找到一个对比实时位姿与光束法平差估计的示例。

### 多条轨迹估计

与单条轨迹评估类似，对于 ROS 2，运行

```
ros2 run rpg_trajectory_evaluation analyze_trajectories \
  euroc_vislam_mono.yaml --output_dir=./results/euroc_vislam_mono --results_dir=./results/euroc_vislam_mono --platform laptop --odometry_error_per_dataset --plot_trajectories --rmse_table --rmse_boxplot --mul_trials=10
```
否则在 uv 环境下运行

```
uv run analyze_trajectories \
  euroc_vislam_mono.yaml --output_dir=./results/euroc_vislam_mono --results_dir=./results/euroc_vislam_mono --platform laptop --odometry_error_per_dataset --plot_trajectories --rmse_table --rmse_boxplot --mul_trials=10
```

这些命令会在 `results_dir` 下查找 `<platform>` 文件夹，并分析如下所述的、由配置文件指定的算法与数据集组合。

#### 数据集组织方式
`results` 下的数据集组织为

```
<platform>
├── <alg1>
│   ├── <platform>_<alg1>_<dataset1>
│   ├── <platform>_<alg1>_<dataset2>
│   └── ......
└── <alg2>
│   ├── <platform>_<alg2>_<dataset1>
│   ├── <platform>_<alg2>_<dataset2>
    ├── ......
......
```

每个子文件夹的格式与上文所述相同。
你需要为脚本 `analyze_trajectories` 指定要分析的算法和数据集。
我们使用 `analyze_trajectories_config` 下的配置文件来指定这些细节。例如，在 `euroc_vio_mono_stereo.yaml` 中

```
Datasets:
  MH_01:        ---> 数据集名称
    label: MH01 ---> 数据集的绘图标签
  MH_03:
    label: MH03
  MH_05:
    label: MH05
  V2_01:
    label: V201
  V2_02:
    label: V202
  V2_03:
    label: V203
Algorithms:
  vio_mono:         ---> 算法名称
    fn: traj_est    ---> 用于确定正确文件名的估计类型
    label: vio_mono ---> 算法的绘图标签
  vio_stereo: 
    fn: traj_est
    label: vio_stereo
RelDistances: []   ---> 用于指定相对误差中的子轨迹长度，见下文。
RelDistancePercentages: []
```

将分析以下文件夹

```
├── vio_mono
│   ├── laptop_vio_mono_MH_01
│   ├── laptop_vio_mono_MH_03
│   ├── laptop_vio_mono_MH_05
│   ├── laptop_vio_mono_V2_01
│   ├── laptop_vio_mono_V2_02
│   └── laptop_vio_mono_V2_03
└── vio_stereo
    ├── laptop_vio_stereo_MH_01
    ├── laptop_vio_stereo_MH_03
    ├── laptop_vio_stereo_MH_05
    ├── laptop_vio_stereo_V2_01
    ├── laptop_vio_stereo_V2_02
    └── laptop_vio_stereo_V2_03
```

##### 为相对位姿误差指定子轨迹长度
相对位姿误差由不同长度的子轨迹计算得到，可通过配置文件中的以下字段指定
* `RelDistances`：一组长度，将用于所有数据集
* `RelDistancePercentages`：长度将按每个数据集总长度的特定百分比独立选取。**该设置会被 `RelDistances` 覆盖**。
如果以上两项都未指定，将使用默认百分比（参见 `src/trajectory.py`）。


#### 输出
评估过程会在每个结果文件夹中生成 `saved_results` 文件夹，
与单条轨迹估计的评估相同。
此外，它还会在 `results` 文件夹下生成用于对比不同算法的图表和文本文件：
* 在 `<platform>_<dataset>_results` 文件夹中，可以找到该数据集上的轨迹俯视/侧视图，以及相对位姿误差的箱线图。
* `all_translation/rotation_rmse.pdf`：所有数据集上多次运行 RMSE 的箱线图。
* `<platform>_translation_rmse<algorithm_dataset_string>.txt`：汇总所有配置 RMSE 的 `Latex` 表格。`<algorithm_dataset_string>` 是由所评估的算法和数据集生成的标识符。表格中的数值按 `mean, median (min, max)` 的格式，由多次试验的误差统计得到。

这些表格可直接用于 `Latex` 文件。

以下是一些示例图表（来自 `analyze_trajectories_config/euroc_vislam_mono.yaml`），用于对比不同算法的性能

![overall_top_traj_mh03](./doc/MH_03_trajectory_top.png)
![overall_rel_err_mh03](./doc/MH_03_trans_yaw_error.png)

#### 参数
配置：
* `config`：`analyze_trajectories_config` 下的配置文件

路径：
* `--results_dir`：将在此文件夹下查找 `<platform>` 文件夹。默认：工具箱文件夹中的 `results` 文件夹。
* `--output_dir`：所有图表和文本文件的输出文件夹。默认：工具箱文件夹中的 `results` 文件夹。
* `--platform`：要在 `<results_dir>` 下查找的结果文件夹。默认：`laptop`

分析选项：
* `--mul_trials`：要分析的试验次数。默认：`None`。若某些算法-数据集配置的运行次数更少，则只考虑可用的那些。

* `--odometry_error_per_dataset`：是否为每个数据集计算相对误差。默认：`False`。
* `--overall_odometry_error`：是否计算并对比不同算法在所有数据集上的总体里程计误差。默认：`False`。

* `--rmse_table`：是否生成平移 RMSE（绝对误差）表格。默认：`False`。
  * `--rmse_table_median_only`：默认情况下，`--rmse_table` 选项会保存多次运行的中位数/均值/最小值/最大值。使用该选项则只保存中位数。
  * `--rmse_boxplot`：是否为不同数据集的 RMSE 绘制箱线图（仅在分析多次试验结果时有效）。默认：`False`。

* `--plot_trajectories`：是否绘制轨迹。默认：`False`。默认会生成很多图表，其中一些可以通过以下选项关闭。
  * `--no_plot_side`：不绘制侧视图
  * `--no_plot_aligned`：不绘制真值与估计之间的对齐连线
  * `--no_plot_traj_per_alg`：不为每个算法单独生成图表

其他：
* `--recalculate_errors:`：是否清除缓存并重新计算全部内容。默认：`False`。
* `--png`：将图表保存为 png 而不是 pdf。默认：`False`
* `--dpi`：允许以更高的 dpi 保存。默认：300
* `--no_sort_names`：绘图/写出结果时不排序数据集和算法的名称（使用配置文件中的顺序）。默认：名称会被排序。

## 工具

### 数据集工具
本包提供了若干工具，用于准备待分析的数据集。既可以通过 `ros2 run rpg_trajectory_evaluation <tool>` 运行，也可以直接在 uv 环境下用 `uv run <tool>` 运行。具体包括：
* `asl_groundtruth_to_pose`：将 EuRoC 风格格式转换为本工具箱使用的格式。
* `bag_to_pose`：从 ROS 2 bag 中提取 `PoseStamped`/`PoseWithCovarianceStamped` 并转换为所需格式。该工具需要先 source ROS 2 环境。
* `transform_trajectory`：用给定的变换对本文格式的位姿文件进行变换，适用于在分析前对手眼标定结果应用到真值/估计上。

### 其他工具
本包还提供：
* `recursive_clean_results_dir`：递归删除所有 `saved_results` 目录。
* `change_eval_cfg_recursive`：递归修改给定结果文件夹内的评估参数。

## 定制
大部分误差计算都是通过 `Trajectory` 类（`ros2_ws/src/rpg_trajectory_evaluation/rpg_trajectory_evaluation/trajectory.py`）完成的。
如果你想定制评估流程，可以直接使用这个类。
该类的 API 相当简单

```python
from rpg_trajectory_evaluation import Trajectory

# 使用结果文件夹初始化。
# 你也可以在初始化时指定子轨迹长度和对齐参数。
traj = Trajectory(result_dir)

# 计算绝对误差
traj.compute_absolute_error()

# 计算 `subtraj_lengths` 处的相对误差。
traj.compute_relative_errors(subtraj_lengths)

# 根据整条轨迹长度计算出的子轨迹长度，计算相对误差。
traj.compute_relative_errors()

# 将相对误差保存到 `cached_rel_err.pickle`
traj.cache_current_error()

# 将误差统计写入 yaml 文件
traj.write_errors_to_yaml()

# 静态方法：从结果文件夹中删除缓存的误差
Trajectory.remove_cached_error(result_dir)
```

误差计算完成后，绝对误差和相对误差会保存在轨迹对象中，之后可以访问：
* 绝对误差：`traj.abs_errors`。
这是一个字典，保存所有位姿的绝对误差及其统计信息。
详见 `Trajectory.compute_absolute_error` 函数。

* 相对误差：`traj.rel_errors`。
这是一个字典，保存不同距离下的相对误差（以距离为键）。
详见 `Trajectory.compute_relative_error_at_subtraj_len` 函数。

借助这些接口，应该很容易访问所有已计算的误差以进行定制分析。

## 致谢与贡献者
贡献者名单参见 `package.yaml`。

可能存在一些开源代码被纳入本工具箱，但我们遗漏了其许可/版权信息的情况。
如果你发现此类问题，请提交 issue。

## 资助声明
本工具箱的开发得到了瑞士国家科学基金会（SNSF）通过国家机器人研究能力中心（NCCR Robotics）、SNSF-ERC Starting Grant 以及 DARPA FLA 项目的支持。
