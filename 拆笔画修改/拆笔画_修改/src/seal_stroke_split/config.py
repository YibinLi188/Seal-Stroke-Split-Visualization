from dataclasses import asdict, dataclass


@dataclass(slots=True)
class SplitConfig:
    threshold: int = 0
    padding: int = 3
    min_component_area: int = 8
    direction_window: int = 2
    split_angle_deg: float = 55.0
    min_segment_points: int = 5
    bridge_radius: int = 1
    merge_angle_deg: float = 28.0
    through_angle_deg: float = 32.0
    max_endpoint_gap: float = 3.2
    tiny_segment_points: int = 6
    min_region_area: int = 10
    # Retained for compatibility with earlier experiment arguments. Pixel
    # assignment is now exclusive, so this value no longer enables sharing.
    overlap_margin: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)
