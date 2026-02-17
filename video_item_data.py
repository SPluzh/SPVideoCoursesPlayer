from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class VideoItemData:
    filename: str
    duration: float
    resolution: str
    file_size: int
    watched_percent: float
    thumbnail_path: Optional[str]
    thumbnails_list: List[str]
    last_position: float
    marker_count: int
    is_favorite: bool
    tags: List[dict] = field(default_factory=list)
