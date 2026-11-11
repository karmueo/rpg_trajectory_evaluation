# rpg_trajectory_evaluation

本工具评估视觉（惯性）里程计轨迹，支持轨迹对齐、绝对轨迹误差（ATE）和相对误差（RE），输出 YAML 统计、图表及单次评估的中文报告。适用于 Python >=3.10（uv 环境固定 3.12）、Ubuntu 24.04 / ROS 2 Jazzy。以下从仓库根目录开始，使用 Bash；先安装 uv，或选择 ROS 2 构建方式。输入为带秒级时间戳的真值与估计位姿，格式见[准备数据](#准备数据)。依赖与版本依据：[pyproject.toml](pyproject.toml)、[.python-version](.python-version)、[setup.py](ros2_ws/src/rpg_trajectory_evaluation/setup.py)。

学术使用请引用：Zichao Zhang, Davide Scaramuzza, *A Tutorial on Quantitative Trajectory Evaluation for Visual(-Inertial) Odometry*, IROS 2018（[论文](https://rpg.ifi.uzh.ch/docs/IROS18_Zhang.pdf)）。

## 安装

### 独立 Python 环境（uv）

```bash
# 在仓库根目录安装 Python 依赖并创建 .venv
uv sync
```

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| 无（本流程无需额外参数） | 使用仓库开发环境配置 | 输入：pyproject.toml、uv.lock；输出：.venv | Python 版本见 .python-version；包含 numpy、matplotlib、colorama、PyYAML 和开发依赖 |

后续使用 `uv run`，无需激活虚拟环境。图表可选用 LaTeX（`latex`、`dvipng`）；未安装时回退到 matplotlib mathtext。

### ROS 2 包（替代方式）

已安装 ROS 2 Jazzy、rosdep 和 colcon 时使用此分支。`ros2 run` 使用系统 Python；uv 环境不能代替 ROS 2 包依赖。

```bash
# 在当前终端加载 ROS 2 Jazzy 环境
source \
  /opt/ros/jazzy/setup.bash
```

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| 脚本路径（位置参数） | 选择要加载的环境脚本 | 输入文件；修改当前 Shell 环境 | 必填，无默认值；后续也用于 install/setup.bash |

```bash
# 从仓库根目录安装 ROS 2 包依赖
rosdep install \
  --from-paths ros2_ws/src \
  --ignore-src \
  -r \
  -y
```

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| --from-paths | 从源码路径读取包依赖 | 输入目录 | 本流程指定 ros2_ws/src |
| --ignore-src | 跳过源码中已有的包 | 行为控制项（非输入输出） | 本流程启用 |
| -r | 遇到错误后继续处理其他依赖 | 行为控制项（非输入输出） | 本流程启用；结束后需确认没有未解决的依赖错误 |
| -y | 自动同意安装提示 | 行为控制项（非输入输出） | 本流程启用；可能需要系统安装权限 |

```bash
# 进入 ROS 2 工作区
cd \
  ros2_ws
```

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| 目录（位置参数） | 设置当前工作目录 | 输入目录 | 本流程必填；此处为仓库下的 ros2_ws |

```bash
# 构建 ROS 2 包并使用符号链接安装
colcon build \
  --symlink-install
```

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| --symlink-install | 对支持的文件使用符号链接 | 行为控制项；输出：工作区 build/、install/、log/ | 本流程启用 |

```bash
# 在当前终端加载构建后的包
source \
  install/setup.bash
```

此处仍在 `ros2_ws/`。后续示例从仓库根目录执行；新终端需重新加载 `/opt/ros/jazzy/setup.bash` 和工作区 `install/setup.bash`。

## 准备数据

### 位姿

每次运行使用一个结果目录，放入 `stamped_groundtruth.txt` 和 `stamped_traj_estimate.txt`。两者均为空格分隔，每行格式如下；时间戳以秒为单位，四元数顺序为 `qx qy qz qw`。

```text
# timestamp tx ty tz qx qy qz qw
1403636580.0135555 0.0125828 -0.0015615 -0.0401530 -0.0513115 -0.8092917 0.0008563 0.5851610
```

多次试验的估计文件使用 `stamped_traj_estimate0.txt` 至 `stamped_traj_estimateN-1.txt`，共用真值文件；单次试验不加数字后缀。其他估计类型对应文件为 `pose_graph` → `stamped_pose_graph_estimate.txt`、`ba_estimate` → `stamped_ba_estimate.txt`，见[文件名映射](ros2_ws/src/rpg_trajectory_evaluation/rpg_trajectory_evaluation/fn_constants.py)。

### 评估参数

可在结果目录手动创建 `eval_cfg.yaml`；存在时须同时包含两个配置项。省略文件时默认使用 `sim3` 和全部位姿。

```yaml
align_type: sim3
align_num_frames: -1
```

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| align_type（YAML 配置） | 设置绝对误差计算前的对齐方式 | 输入值 | 文件不存在时 sim3；支持 sim3（相似变换，单目）、se3（刚体变换，双目）、posyaw（平移与偏航角，视觉惯性）、none（不对齐） |
| align_num_frames（YAML 配置） | 设置从开头选取的对齐位姿数 | 输入值 | 文件不存在时 -1（全部）；也可指定正整数，须有足够位姿供对应对齐方式使用 |

### 起始与结束时间

可在结果目录手动创建 `start_end_time.yaml`，按真值时间筛选；两个键均可省略。不创建文件时不额外限制时间范围，仍只评估能够匹配的位姿。

```yaml
start_time_sec: 1403636580.0
end_time_sec: 1403636600.0
```

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| start_time_sec（YAML 配置） | 设置开始时间，包含端点 | 输入值 | 默认负无穷；支持秒级时间戳，上述值为示例 |
| end_time_sec（YAML 配置） | 设置结束时间，包含端点 | 输入值 | 默认正无穷；支持不早于开始时间的秒级时间戳，上述值为示例 |

配置与时间筛选依据：[trajectory.py](ros2_ws/src/rpg_trajectory_evaluation/rpg_trajectory_evaluation/trajectory.py)、[trajectory_loading.py](ros2_ws/src/rpg_trajectory_evaluation/rpg_trajectory_evaluation/trajectory_loading.py)。显式输入两个文件时，配置读取目录为对比轨迹所在目录；文件夹输入时为该文件夹。

## 运行评估

### 单条轨迹估计

```bash
# 评估仓库内的 EuRoC 单次试验示例并生成图表
uv run analyze_trajectory_single \
  results/euroc_mono_stereo/laptop/vio_mono/laptop_vio_mono_MH_05
```

默认在输入目录生成 `saved_results/result.md`、`saved_results/<est_type>/` 下的 `absolute_err_statistics_<align_type>_<align_frames>.yaml` 和 `relative_error_statistics_<len>.yaml`，以及 `plots/<est_type>/` 下的图表。相对误差缓存位于 `saved_results/<est_type>/cached/cached_rel_err.pickle`；多次试验文件带后缀，汇总文件以 `mt_` 开头。三维图包括 `trajectory_3d_gt_<align>`（真值）、`trajectory_3d_est_<align>`（对齐后的对比轨迹）与 `trajectory_3d_<align>`（真值和对齐估计）；`result.md` 中依次为图 3、图 4、图 5。所有轨迹图（图 1 至图 5）用实心小圆点标出起点、用叉号标出终点；同时显示真值与对比轨迹的图（图 1、图 2、图 5）线条为 70% 不透明，仅显示单条轨迹的图（图 3、图 4）保持不透明。使用 `--no_plot` 仍会生成报告。

参数依据：[单次评估入口](ros2_ws/src/rpg_trajectory_evaluation/rpg_trajectory_evaluation/cli/analyze_trajectory_single.py)。

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| input_path（位置参数） | 指定结果目录或真值轨迹 | 输入目录或文件 | 必填，无默认值；文件输入时必须提供 comparison_path |
| comparison_path（位置参数） | 显式选择对比轨迹 | 输入文件 | 默认未设置；目录输入时自动识别，文件输入时必填 |
| --output_dir | 设置统计与报告的输出根目录 | 输出目录 | 默认：目录输入时为该目录，文件输入时为对比轨迹所在目录 |
| --plots_dir | 单独设置图表根目录 | 输出目录 | 默认：<output_dir>/plots |
| --mul_trials | 设置试验次数 | 输入值 | 默认 None（单次）；支持正整数；大于 1 时使用传统文件名及从 0 开始的后缀 |
| --mul_plot_idx | 选择用于绘图的试验索引 | 输入值 | 默认 [0]；当前仅支持选择一个索引，按成功加载的试验列表取值 |
| --est_types、--est_type | 按固定文件名选择一种或多种估计类型 | 输入值 | 默认自动识别；支持 traj_est、pose_graph、ba_estimate；显式传入时至少一个值 |
| --recalculate_errors | 删除相对误差缓存和匹配文件后重算 | 行为控制项（非输入输出） | 默认 False；修改输入或评估配置后使用 |
| --png | 使用 PNG 图表格式 | 行为控制项（非输入输出） | 默认即为 PNG；与 --pdf 同传时 PDF 优先 |
| --pdf | 使用 PDF 图表格式 | 行为控制项（非输入输出） | 默认 False |
| --plot_scale_traj | 添加按尺度误差着色的轨迹图，耗时较长 | 行为控制项（非输入输出） | 默认 False |
| --plot、--no_plot | 启用或关闭绘图 | 行为控制项（非输入输出） | 默认启用；同时传入时以后出现者为准 |
| -h、--help | 显示帮助并退出 | 行为控制项（非输入输出） | 默认不启用 |

自动识别仅扫描目录第一层 `.txt` 文件，跳过空行/注释后的首条记录需至少包含 8 列数值；文件名含 `groundtruth`、`ground_truth` 或独立 `gt` 字段时作为真值候选。候选不唯一时需在交互终端选择，或显式传入文件。显式对比文件不能与 `--est_types` 或 `--mul_trials > 1` 同用。

下列路径均为需替换的示例值：

```bash
# 显式选择真值和对比轨迹，并只生成统计与报告
uv run analyze_trajectory_single \
  /path/to/groundtruth.txt \
  /path/to/comparison.txt \
  --no_plot
```

第一个位置参数也可换为结果目录，保留第二个位置参数以覆盖自动选择。

```bash
# 按传统命名评估实时位姿和位姿图轨迹
uv run analyze_trajectory_single \
  /path/to/result_folder \
  --est_types traj_est pose_graph
```

ROS 2 分支需先加载环境，再从仓库根目录执行：

```bash
# 通过 ROS 2 运行相同的单次评估入口
ros2 run rpg_trajectory_evaluation analyze_trajectory_single \
  results/euroc_mono_stereo/laptop/vio_mono/laptop_vio_mono_MH_05
```

参数与上表一致；批量评估和下列工具也可将 `uv run <入口>` 替换为 `ros2 run rpg_trajectory_evaluation <入口>`。

### 多条轨迹估计

输入目录须按 `<results_dir>/<platform>/<algorithm>/<platform>_<algorithm>_<dataset>/` 组织，每个末级目录采用[准备数据](#准备数据)中的文件格式。按需编辑 [analyze_trajectories_config](analyze_trajectories_config) 中的配置；以下为可编辑的最小示例：

```yaml
Datasets:
  MH_05:
    label: MH05
Algorithms:
  vio_mono:
    fn: traj_est
    label: vio_mono
RelDistances: []
RelDistancePercentages: []
```

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| Datasets（YAML 配置） | 设置数据集名称和绘图文字 | 输入值 | 必填，无默认值；每个数据集须有 label，可选 title |
| Algorithms（YAML 配置） | 设置算法名称、估计类型和绘图标签 | 输入值 | 必填，无默认值；每个算法须有 fn 和 label；fn 支持 traj_est、pose_graph、ba_estimate |
| RelDistances（YAML 配置） | 设置所有数据集共用的子轨迹长度（米） | 输入值 | 默认 []；非空时优先于 RelDistancePercentages |
| RelDistancePercentages（YAML 配置） | 按各数据集轨迹总长设置子轨迹比例 | 输入值 | 未指定或为空且 RelDistances 为空时使用 [0.1, 0.2, 0.3, 0.4, 0.5]；使用小数比例而非百分数整数 |

配置解析与默认比例依据：[批量评估入口](ros2_ws/src/rpg_trajectory_evaluation/rpg_trajectory_evaluation/cli/analyze_trajectories.py)、[Trajectory](ros2_ws/src/rpg_trajectory_evaluation/rpg_trajectory_evaluation/trajectory.py)。

```bash
# 对比示例中的算法和数据集，汇总十次试验并生成表格与图表
uv run analyze_trajectories \
  analyze_trajectories_config/euroc_vislam_mono.yaml \
  --output_dir=./results/euroc_vislam_mono \
  --results_dir=./results/euroc_vislam_mono \
  --platform laptop \
  --odometry_error_per_dataset \
  --plot_trajectories \
  --rmse_table \
  --rmse_boxplot \
  --mul_trials=10
```

每个输入结果目录下生成 `saved_results/`；汇总输出写入 `--output_dir`，包括 `<platform>_<dataset>_results/` 下的图表、`all_translation_rmse` / `all_rotation_rmse` 箱线图（多次试验），以及 `<platform>_translation_rmse_<标识符>.txt` LaTeX 表格。多次试验表格默认使用 `mean, median (min - max)`。批量入口不生成单次入口的 `result.md`。

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| config（位置参数） | 指定算法和数据集配置 | 输入文件 | 必填，无默认值；相对路径先按当前目录查找，不存在时按当前目录下 analyze_trajectories_config/ 查找 |
| --results_dir | 设置包含平台目录的结果根目录 | 输入目录 | 默认：当前工作目录下 results/ |
| --output_dir | 设置汇总图表和文本输出位置 | 输出目录 | 默认：当前工作目录下 results/；同时复制配置文件到此目录 |
| --platform | 选择平台目录及结果名前缀 | 输入值 | 默认 laptop；支持与实际目录名一致的字符串，无枚举限制 |
| --mul_trials | 设置试验次数 | 输入值 | 默认 None（单次）；多次试验使用从 0 开始的数字后缀，只汇总成功加载的试验 |
| --odometry_error_per_dataset | 分数据集汇总相对误差 | 行为控制项（非输入输出） | 默认 False |
| --overall_odometry_error | 汇总所有数据集的相对误差及表格 | 行为控制项（非输入输出） | 默认 False；各数据集子轨迹长度相同时另生成总体对比图 |
| --rmse_table | 输出平移 RMSE LaTeX 表格 | 行为控制项（非输入输出） | 默认 False |
| --rmse_table_median_only | 表格仅保留中位数 | 行为控制项（非输入输出） | 默认 False；配合 --rmse_table |
| --rmse_boxplot | 绘制 RMSE 箱线图 | 行为控制项（非输入输出） | 默认 False；仅多次试验有效 |
| --write_time_statistics | 写出起止时间及测量数统计 | 行为控制项；输出文件 | 默认 False；输出到各数据集结果目录的 <dataset>_meas_stats.json |
| --plot_trajectories | 绘制轨迹图 | 行为控制项（非输入输出） | 默认 False |
| --no_plot_side | 关闭侧视图 | 行为控制项（非输入输出） | 默认不关闭 |
| --no_plot_aligned | 关闭真值与估计的对齐连线 | 行为控制项（非输入输出） | 默认不关闭 |
| --no_plot_traj_per_alg | 关闭每个算法的独立轨迹图 | 行为控制项（非输入输出） | 默认不关闭 |
| --recalculate_errors | 清除缓存与匹配文件后重算 | 行为控制项（非输入输出） | 默认 False |
| --png | 改用 PNG 图表格式 | 行为控制项（非输入输出） | 默认 False，默认格式 PDF |
| --dpi | 设置图表分辨率 | 输入值 | 默认 300；整数 |
| --no_sort_names | 保留配置中的算法和数据集顺序 | 行为控制项（非输入输出） | 默认不启用，按名称排序 |
| -h、--help | 显示帮助并退出 | 行为控制项（非输入输出） | 默认不启用 |

## 工具

### 数据集工具

下列 `/path/to/...` 和话题名均需替换。参数及输出依据：[数据集工具源码](ros2_ws/src/rpg_trajectory_evaluation/rpg_trajectory_evaluation/cli/dataset_tools)。

```bash
# 将 EuRoC / ASL 真值 CSV 转为秒级时间戳和 qx qy qz qw 格式
uv run asl_groundtruth_to_pose \
  /path/to/data.csv \
  --output stamped_groundtruth.txt
```

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| gt（位置参数） | 指定 EuRoC / ASL 真值 CSV | 输入文件 | 必填，无默认值；原时间戳为纳秒，四元数为 qw qx qy qz |
| --output | 设置转换后的文件名或绝对路径 | 输出文件 | 默认 groundtruth.txt；相对路径基于输入 CSV 所在目录 |
| -h、--help | 显示帮助并退出 | 行为控制项（非输入输出） | 默认不启用 |

`bag_to_pose` 需要 ROS 2 Python 依赖，先在当前终端加载 ROS 2 和构建后的工作区环境，见[ROS 2 安装](#ros-2-包替代方式)。

```bash
# 从 ROS 2 bag 的位姿话题提取轨迹
ros2 run rpg_trajectory_evaluation bag_to_pose \
  /path/to/bag \
  /pose_topic \
  --output stamped_poses.txt
```

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| bag（位置参数） | 指定 ROS 2 bag | 输入目录 | 必填，无默认值 |
| topic（位置参数） | 选择位姿话题 | 输入值 | 必填，无默认值；须为 bag 内实际话题 |
| --msg_type | 指定位姿消息类型 | 输入值 | 默认 auto；支持 auto、PoseStamped、PoseWithCovarianceStamped |
| --storage_id | 指定 rosbag2 存储插件 | 输入值 | 默认空字符串，由 rosbag2 自动选择；可用值依赖已安装插件 |
| --output | 设置轨迹输出文件名或绝对路径 | 输出文件 | 默认 stamped_poses.txt；相对路径基于 bag 目录的父目录 |
| -h、--help | 显示帮助并退出 | 行为控制项（非输入输出） | 默认不启用 |

```bash
# 将固定变换右乘到轨迹位姿，可用于应用手眼标定结果
uv run transform_trajectory \
  /path/to/trajectory.txt \
  /path/to/transformation.csv
```

输出为输入轨迹同目录的 `transformed_poses.txt`，已有同名文件会被覆盖。输入轨迹须保留首行标题，脚本会跳过该行。

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| trajectory（位置参数） | 指定待变换轨迹 | 输入文件 | 必填，无默认值；空格分隔，含标题和 timestamp tx ty tz qx qy qz qw |
| transformation（位置参数） | 指定固定变换矩阵 | 输入文件 | 必填，无默认值；4×4 矩阵，每行逗号分隔；计算 T_new = T_old × transformation |
| -h、--help | 显示帮助并退出 | 行为控制项（非输入输出） | 默认不启用 |

### 其他工具

以下操作会修改或删除结果目录中的文件，执行前确认目标路径。依据：[配置修改工具](ros2_ws/src/rpg_trajectory_evaluation/rpg_trajectory_evaluation/cli/change_eval_cfg_recursive.py)、[结果清理工具](ros2_ws/src/rpg_trajectory_evaluation/rpg_trajectory_evaluation/cli/recursive_clean_results_dir.py)。

```bash
# 递归改写已有 eval_cfg.yaml 的两个对齐参数
uv run change_eval_cfg_recursive \
  /path/to/results \
  sim3 \
  -1
```

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| root_dir（位置参数） | 指定递归搜索范围 | 输入目录；目录内配置为输入兼输出 | 必填，无默认值；仅修改已有 eval_cfg.yaml |
| align_type（位置参数） | 设置对齐类型 | 输入值 | 必填，无默认值；评估支持 sim3、se3、posyaw、none |
| align_n（位置参数） | 设置对齐位姿数 | 输入值 | 必填，无默认值；-1 表示全部，也可使用足够数量的正整数 |
| -h、--help | 显示帮助并退出 | 行为控制项（非输入输出） | 默认不启用 |

修改后再次评估时使用 `--recalculate_errors`。

```bash
# 递归删除目标目录内所有 saved_results 目录及其内容
uv run recursive_clean_results_dir \
  /path/to/results
```

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| root_dir（位置参数） | 指定递归搜索范围 | 输入目录；其内部匹配目录被删除 | 必填，无默认值 |
| --res_dir | 设置待删除的目录名 | 输入值；行为控制项 | 默认 saved_results；支持自定义目录名，匹配目录及全部内容直接删除，无确认提示 |
| -h、--help | 显示帮助并退出 | 行为控制项（非输入输出） | 默认不启用 |

## 定制

在已配置依赖的 Python 环境中使用以下代码，将路径替换为已有结果目录。接口与参数依据：[Trajectory 类](ros2_ws/src/rpg_trajectory_evaluation/rpg_trajectory_evaluation/trajectory.py)。

```python
# 导入轨迹评估接口
from rpg_trajectory_evaluation import Trajectory

# 加载并对齐指定目录中的轨迹
traj = Trajectory("/path/to/result_folder")
# 计算绝对误差
traj.compute_absolute_error()
# 按预设长度计算相对误差；也可传入米制长度列表
traj.compute_relative_errors()
# 保存相对误差缓存
traj.cache_current_error()
# 写入 YAML 统计
traj.write_errors_to_yaml()
```

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| results_dir（构造参数） | 设置结果根目录 | 输入兼输出目录 | 必填，无默认值；目录须存在 |
| platform（构造参数） | 设置平台标签 | 输入值 | 默认空字符串 |
| alg_name（构造参数） | 设置算法标签 | 输入值 | 默认空字符串 |
| dataset_name（构造参数） | 设置数据集标签 | 输入值 | 默认空字符串 |
| align_type（构造参数） | 设置默认对齐方式 | 输入值 | 默认 sim3；被 eval_cfg.yaml 覆盖；支持值见评估参数表 |
| align_num_frames（构造参数） | 设置默认对齐位姿数 | 输入值 | 默认 -1；被 eval_cfg.yaml 覆盖；支持值见评估参数表 |
| suffix（构造参数） | 设置结果文件后缀 | 输入值 | 默认空字符串 |
| est_type（构造参数） | 设置结果分类目录 | 输入值 | 默认 traj_est |
| nm_gt（构造参数） | 指定真值文件名 | 输入文件 | 默认 stamped_groundtruth.txt；相对路径基于 data_dir |
| nm_est（构造参数） | 指定估计文件名 | 输入文件 | 默认 stamped_traj_estimate.txt；相对路径基于 data_dir |
| nm_matches（构造参数） | 指定匹配文件名 | 输入兼输出文件 | 默认 stamped_est_gt_matches.txt；相对路径基于 saved_results/<est_type>/ |
| preset_boxplot_distances（构造参数） | 设置米制子轨迹长度列表 | 输入值 | 默认 []；非空时优先 |
| preset_boxplot_percentages（构造参数） | 设置子轨迹长度比例列表 | 输入值 | 默认 []；未指定长度和比例时使用 [0.1, 0.2, 0.3, 0.4, 0.5] |
| data_dir（构造参数） | 单独指定轨迹与配置目录 | 输入目录 | 默认 None，使用 results_dir |
| subtraj_lengths（compute_relative_errors 参数） | 设置此次计算的米制长度列表 | 输入值 | 默认 []，使用初始化时的预设长度；例如 [10.0, 20.0] |
| 无（compute_absolute_error） | 无调用参数 | 输出：traj.abs_errors 字典 | 不适用 |
| 无（cache_current_error） | 无调用参数 | 输出：saved_results/<est_type>/cached/ 中的缓存 | 不适用 |
| 无（write_errors_to_yaml） | 无调用参数 | 输出：saved_results/<est_type>/ 中的 YAML | 不适用 |

绝对误差保存在 `traj.abs_errors`；相对误差保存在以子轨迹长度为键的 `traj.rel_errors`。需要主动清理缓存时，在重新构造对象之前调用：

```python
# 删除指定结果目录中默认估计类型的相对误差缓存
Trajectory.remove_cached_error("/path/to/result_folder", est_type="traj_est")
```

| 支持的参数／配置项 | 参数作用 | 输入/输出 | 默认值/支持的值 |
| --- | --- | --- | --- |
| data_dir | 指定结果根目录 | 输入目录；内部缓存被删除 | 必填，无默认值 |
| est_type | 选择估计类型目录 | 输入值 | 默认空字符串；清理默认轨迹结果时显式传 traj_est |
| suffix | 选择缓存文件后缀 | 输入值 | 默认空字符串 |
