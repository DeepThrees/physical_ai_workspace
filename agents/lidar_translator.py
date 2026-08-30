"""ROS2 /scan LiDAR 거리를 LLM이 읽을 수 있는 텍스트로 번역하는 노드.

정면(0°), 좌측(+90°), 우측(-90°)의 ±5° 최솟값을 추출해
`workspace_memory/environment_summary.txt`에 2Hz로 덮어쓴다.
"""
from __future__ import annotations

import math
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

NODE_NAME = "lidar_translator_node"
SCAN_TOPIC = "/scan"
WRITE_INTERVAL_SEC = 0.5
WINDOW_DEG = 5.0

FRONT_ANGLE_RAD = 0.0
LEFT_ANGLE_RAD = math.pi / 2.0
RIGHT_ANGLE_RAD = -math.pi / 2.0

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "workspace_memory" / "environment_summary.txt"


class LidarTranslatorNode(Node):
    """`/scan`을 구독해 좌/우/정면 거리 요약을 파일로 내보낸다."""

    def __init__(self) -> None:
        super().__init__(NODE_NAME)
        self._last_emit_monotonic = 0.0
        self.create_subscription(
            LaserScan,
            SCAN_TOPIC,
            self._on_scan,
            qos_profile_sensor_data,
        )
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.get_logger().info(
            f"{SCAN_TOPIC} 구독 시작. 요약은 {WRITE_INTERVAL_SEC:.1f}s 간격으로 "
            f"{OUTPUT_PATH}에 저장됩니다."
        )

    def _on_scan(self, msg: LaserScan) -> None:
        now = time.monotonic()
        if now - self._last_emit_monotonic < WRITE_INTERVAL_SEC:
            return
        self._last_emit_monotonic = now

        front = _window_min_range(msg, FRONT_ANGLE_RAD)
        left = _window_min_range(msg, LEFT_ANGLE_RAD)
        right = _window_min_range(msg, RIGHT_ANGLE_RAD)

        summary = (
            f"현재 전방 여유 공간은 {front:.2f}m, "
            f"좌측은 {left:.2f}m, "
            f"우측은 {right:.2f}m 입니다."
        )
        _write_summary(summary)
        self.get_logger().info(summary)


def _angle_to_index(msg: LaserScan, target_rad: float) -> int:
    """스캔 각도 범위로 정규화한 뒤 가장 가까운 range 인덱스를 반환한다."""
    increment = msg.angle_increment
    n = len(msg.ranges)
    if n == 0 or abs(increment) < 1e-12:
        return 0

    two_pi = 2.0 * math.pi
    angle = target_rad
    while angle < msg.angle_min:
        angle += two_pi
    while angle > msg.angle_max:
        angle -= two_pi

    index = int(round((angle - msg.angle_min) / increment))
    return max(0, min(n - 1, index))


def _is_full_scan(msg: LaserScan) -> bool:
    """스캔이 거의 360°를 덮으면 인덱스 wrap-around를 허용한다."""
    span = abs(msg.angle_max - msg.angle_min)
    return span + abs(msg.angle_increment) >= (2.0 * math.pi) - 1e-3


def _sanitize_range(value: float, range_max: float) -> float:
    if math.isinf(value) or math.isnan(value):
        return float(range_max)
    return float(value)


def _window_min_range(
    msg: LaserScan,
    target_rad: float,
    window_deg: float = WINDOW_DEG,
) -> float:
    """목표 각도 인덱스 기준 ±window_deg 구간의 최솟값을 반환한다."""
    n = len(msg.ranges)
    range_max = float(msg.range_max)
    if n == 0 or abs(msg.angle_increment) < 1e-12:
        return range_max

    center = _angle_to_index(msg, target_rad)
    half_span = max(
        0,
        int(round(math.radians(window_deg) / abs(msg.angle_increment))),
    )
    wrap = _is_full_scan(msg)

    window: list[float] = []
    for offset in range(-half_span, half_span + 1):
        index = center + offset
        if wrap:
            index %= n
        elif index < 0 or index >= n:
            continue
        window.append(_sanitize_range(msg.ranges[index], range_max))

    return min(window) if window else range_max


def _write_summary(text: str) -> None:
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(text + "\n")


def main() -> None:
    rclpy.init()
    node = LidarTranslatorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
