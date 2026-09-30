import json
import os
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from gui.paths import DATA, RECEIVED

PATH = DATA / "settings.json"
LANGUAGES = (("2", "英语"), ("3", "法语"), ("5", "德语"), ("4", "意大利语"), ("7", "西班牙语"),
             ("1", "日语"), ("8", "韩语"))


@dataclass
class Settings:
    keys: str = str(Path.home() / ".switch" / "prod.keys")
    received: str = str(RECEIVED)
    radio_port: str = ""
    baud: int = 921600
    capture: bool = True
    board_trace: bool = False
    firmware: str = ""
    # The trainer every built Pokemon belongs to.
    ot: str = "PkCamp"
    tid: int = field(default_factory=lambda: random.randint(1, 65535))
    sid: int = field(default_factory=lambda: random.randint(1, 65535))
    language: int = 2
    board_names: dict = field(default_factory=dict)   # MAC -> name the user gave the board
    tool_values: dict = field(default_factory=dict)   # tool key -> {"values": {...}, "extra": {...}}

    def save(self) -> None:
        PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2))
        os.replace(tmp, PATH)

    def trainer(self) -> dict:
        return {"ot": self.ot, "tid": self.tid, "sid": self.sid, "language": self.language, "gender": 0}


def load() -> Settings:
    try:
        data = json.loads(PATH.read_text())
    except (OSError, ValueError):
        settings = Settings()
        settings.save()   # keeps the trainer ids drawn above
        return settings
    known = Settings.__dataclass_fields__
    return Settings(**{k: v for k, v in data.items() if k in known})
