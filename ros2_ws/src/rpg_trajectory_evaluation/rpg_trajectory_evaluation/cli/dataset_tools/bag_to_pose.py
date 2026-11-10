#!/usr/bin/env python3

import os
import sys
import argparse


def _ros2_imports():
    """Import the ROS 2 bag API lazily so the other tools work without ROS."""
    try:
        from rosbag2_py import (
            SequentialReader, StorageOptions, ConverterOptions, StorageFilter,
            Info, get_default_storage_id)
        from rclpy.serialization import deserialize_message
        from rosidl_runtime_py.utilities import get_message
    except ImportError as e:
        raise SystemExit(
            "bag_to_pose requires a ROS 2 environment (rosbag2_py, rclpy, "
            "rosidl_runtime_py). Source your ROS 2 setup first, e.g.\n"
            "  source /opt/ros/jazzy/setup.bash\n"
            "Original error: {}".format(e))
    return (SequentialReader, StorageOptions, ConverterOptions, StorageFilter,
            Info, get_default_storage_id, deserialize_message, get_message)


def _detect_storage_id(bagfile, storage_id):
    """Resolve the rosbag2 storage plugin id for a bag."""
    if storage_id:
        return storage_id
    _, _, _, _, Info, get_default_storage_id, _, _ = _ros2_imports()
    try:
        return Info().read_metadata(bagfile, '').storage_identifier
    except Exception:
        return get_default_storage_id()


def extract(bagfile, pose_topic, msg_type, out_filename, storage_id=''):
    if not os.path.exists(bagfile):
        raise SystemExit("Bag '{0}' does not exist.".format(bagfile))

    (SequentialReader, StorageOptions, ConverterOptions, StorageFilter,
     _, _, deserialize_message, get_message) = _ros2_imports()

    resolved_storage_id = _detect_storage_id(bagfile, storage_id)

    reader = SequentialReader()
    reader.open(
        StorageOptions(uri=bagfile, storage_id=resolved_storage_id),
        ConverterOptions('cdr', 'cdr'))
    reader.set_filter(StorageFilter(topics=[pose_topic]))

    topic_types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    if pose_topic not in topic_types:
        raise SystemExit(
            "Topic '{0}' not found in bag. Available topics: {1}".format(
                pose_topic, sorted(topic_types.keys())))

    type_name = topic_types[pose_topic]
    short_type = type_name.rsplit('/', 1)[-1]
    if msg_type != 'auto' and msg_type != short_type:
        raise SystemExit(
            "Topic '{0}' has type '{1}', but --msg_type '{2}' was requested."
            .format(pose_topic, type_name, msg_type))
    if short_type not in ('PoseStamped', 'PoseWithCovarianceStamped'):
        raise SystemExit(
            "Topic '{0}' has unsupported type '{1}'. Supported types are "
            "geometry_msgs/msg/PoseStamped and "
            "geometry_msgs/msg/PoseWithCovarianceStamped.".format(
                pose_topic, type_name))

    msg_cls = get_message(type_name)

    n = 0
    with open(out_filename, 'w') as f:
        f.write('# timestamp tx ty tz qx qy qz qw\n')
        while reader.has_next():
            topic, data, bag_stamp_ns = reader.read_next()
            if topic != pose_topic:
                continue
            msg = deserialize_message(data, msg_cls)
            stamp = msg.header.stamp
            timestamp = stamp.sec + stamp.nanosec * 1e-9
            if timestamp == 0.0:
                # Fall back to the bag timestamp if the header is empty.
                timestamp = bag_stamp_ns * 1e-9
            pose = (msg.pose.pose
                    if short_type == 'PoseWithCovarianceStamped'
                    else msg.pose)
            p = pose.position
            q = pose.orientation
            f.write('%.12f %.12f %.12f %.12f %.12f %.12f %.12f %.12f\n' %
                    (timestamp, p.x, p.y, p.z, q.x, q.y, q.z, q.w))
            n += 1

    print('wrote {0} pose messages to the file: {1}'.format(n, out_filename))
    return n


def main(argv=None):
    parser = argparse.ArgumentParser(description='''
    Extract PoseStamped/PoseWithCovarianceStamped messages from a ROS 2 bag.
    ''')
    parser.add_argument('bag', help='ROS 2 bag directory')
    parser.add_argument('topic', help='Pose topic')
    parser.add_argument('--msg_type', default='auto',
                        choices=['auto', 'PoseStamped',
                                 'PoseWithCovarianceStamped'],
                        help='expected message type (default: auto-detect)')
    parser.add_argument('--storage_id', default='',
                        help='rosbag2 storage plugin id (default: auto)')
    parser.add_argument('--output', default='stamped_poses.txt',
                        help='output filename')
    args = parser.parse_args(argv)

    out_dir = os.path.dirname(os.path.abspath(args.bag))
    out_fn = os.path.join(out_dir, args.output)

    print('Extract pose from bag '+args.bag+' in topic ' + args.topic)
    print('Saving to file '+out_fn)
    extract(args.bag, args.topic, args.msg_type, out_fn, args.storage_id)
    return 0


if __name__ == '__main__':
    sys.exit(main())
