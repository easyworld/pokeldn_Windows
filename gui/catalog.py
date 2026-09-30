"""What the app offers per game: each tool is an entry point, the tested flags it always gets, the
fields a user fills in, and what to press on the console. Fixed arguments may carry {received}
(the Received folder), {stamp} (the run's time) and {src_var} (a fresh random id)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    flag: str | tuple[str, ...]   # "" is positional; a tuple passes the same value to each flag
    label: str
    kind: str = "text"            # text number choice switch pokemon file multi, or a PKHeX name list:
                                  # species move item ball
    help: str = ""
    default: str | bool = ""
    choices: tuple[tuple[str, str], ...] = ()
    required: bool = False
    group: str = ""               # fields sharing a group render on one card
    invert: bool = False          # a switch that passes its flag when turned off
    unset: tuple[str, ...] = ()   # arguments passed when the field is left empty
    exts: tuple[str, ...] = ()
    when: tuple[str, str] = ()    # (flag, value): the field applies only while that field has that value
    template: str = ""            # the value is passed as template.format(value), e.g. "ball={}"
    limits: tuple[tuple[str, int, str], ...] = ()   # (NAME, highest, why) for NAME=VALUE text

    @property
    def key(self) -> str:
        if isinstance(self.flag, tuple):
            return self.flag[0]
        if self.template:
            return f"{self.flag} {self.template}"
        return self.flag or f"#{self.label}"


@dataclass(frozen=True)
class Tool:
    key: str
    name: str
    script: str
    summary: str
    steps: tuple[str, ...]
    fields: tuple[Field, ...] = ()
    fixed: tuple[str, ...] = ()
    doc: str = ""
    unavailable: str = ""         # why the tool cannot run yet; it is shown greyed out


@dataclass(frozen=True)
class Game:
    key: str
    name: str
    short: str
    doc: str
    tools: tuple[Tool, ...]


VERSIONS = (("firered", "火红"), ("leafgreen", "叶绿"))
LANGUAGES = (("english", "英语"), ("french", "法语"), ("german", "德语"),
             ("italian", "意大利语"), ("spanish", "西班牙语"))
CHANNELS = (("1", "1"), ("6", "6"), ("11", "11"))
FRESH_PID = Field("--fresh-pid", "每次使用新的 PID", "switch", default=True,
                  help="每次交换时生成新的 PID 和加密常数，使已接收过它的存档仍可再次接收。")


def offer(flag: str = "", required: bool = True, help: str = "") -> Field:
    return Field(flag, "要交换的宝可梦", "pokemon", required=required,
                 help=help or "选择宝可梦种类；PKHeX 会生成适用于该游戏的合法宝可梦。")


CARD = ("--news", "")
SAVE_DUMP = ("--buffer-script", "save-dump")
HOOK = ("--buffer-script", "install-resident")
FRLG_PATH = "宝可梦中心 2 楼，第三位接待员，直接交流角，交换中心"

FRLG = Game("frlg", "宝可梦 火红／叶绿", "FRLG", "frlg.md", (
    Tool("frlg-trade-host", "交换", "bin/frlg_trade_host.py",
         "创建直接交流角交换房间，游戏机加入 pokeldn 的小组。",
         ("启动主机，等待日志显示正在主持直接交流角。",
          f"{FRLG_PATH}，选择加入小组，再选择 PkCamp。",
          "选择要交换的宝可梦并确认。",
          "保存后返回交换菜单，等待主机提示，再选择取消和是。"),
         (offer(),
          Field("--version", "版本", "choice", default="firered", choices=VERSIONS, group="游戏机"),
          Field("--language", "语言", "choice", default="english", choices=LANGUAGES, group="游戏机"),
          Field("--channel", "信道", "choice", default="11", choices=CHANNELS)),
         fixed=("--live", "--phy", "auto", "--slot", "0", "--out", "{received}/frlg-{stamp}.pk3"),
         doc="frlg_link.md"),
    Tool("frlg-trade-join", "交换（游戏机创建）", "bin/frlg_trade_join.py",
         "加入游戏机创建的交换小组。",
         ("先启动加入程序，等待扫描到游戏机。",
          f"{FRLG_PATH}，选择成为组长。",
          "出现 PkCamp 后接受，再选择宝可梦并确认。"),
         (offer(),),
         fixed=("--live", "--phy", "auto", "--slot", "0", "--out", "{received}/frlg-{stamp}.pk3"),
         doc="frlg_link.md"),
    Tool("frlg-gift", "神秘礼物", "bin/frlg_mg_host.py",
         "发送神秘卡片或神秘新闻。可在任意宝可梦中心向配送员领取礼物。",
         ("标题画面：神秘礼物、神秘卡片、朋友。新闻则选择第二项神秘新闻。",
          "启动主机，出现 PkCamp 时选择它。",
          "若游戏机询问是否替换卡片，选择是。",
          "两次运行之间退出搜索画面。"),
         (Field("--news", "发送内容", "choice", choices=(
             ("", "神秘卡片"), ("pkcamp", "神秘新闻：华蓝市的一颗树果"),
             ("berry", "神秘新闻：十行内容与一颗树果"))),
          Field("--gift", "神秘卡片", "choice", default="beast-cutscene", when=CARD, choices=(
              ("beast-cutscene", "传说的宝可梦（随最初的伙伴变化）"),
              ("celebi", "时拉比"), ("master-ball", "大师球"),
              ("altering-cave", "变化洞窟"), ("porygon-tm-gift", "多边兽招式学习器礼物"),
              ("solrock-stamp", "日月集章：太阳岩印章"),
              ("lunatone-stamp", "日月集章：月石印章"),
              ("visiting-trainer", "来访训练家"), ("battle-count-card", "对战次数卡片"),
              ("worlds-xp", "世界锦标赛经验值"))),
          Field("--flag-id", "卡片标记 ID", "number", when=CARD,
                help="范围为 1000～1019。游戏机会拒绝已有卡片的 ID；可在两个 ID 之间交替。留空则使用礼物自带的 ID。"),
          Field(("--version", "--expect-console"), "版本", "choice", default="firered",
                choices=VERSIONS, group="游戏机"),
          Field("--language", "语言", "choice", default="english", choices=LANGUAGES, group="游戏机"),
          Field("--channel", "信道", "choice", default="11", choices=CHANNELS)),
         fixed=("--live",), doc="frlg_gift.md"),
    Tool("frlg-code", "游戏机代码", "bin/frlg_mg_host.py",
         "通过神秘礼物在游戏机上运行代码：读取存档或安装逐帧钩子。",
         ("标题画面：神秘礼物、神秘卡片、朋友。",
          "启动主机，出现 PkCamp 时选择它。",
          "保持主机运行直到日志显示结果；转储文件会在几秒后写入。"),
         (Field("--buffer-script", "操作", "choice", default="save-dump", choices=(
             ("trainer-id-probe", "读取训练家 ID（只读）"),
             ("save-dump", "读取部分存档（只读）"),
             ("install-resident", "安装钩子直到下次重启（写入内存）"))),
          Field("--dump-block", "存档区块", "choice", default="sav2", group="存档转储",
                choices=(("sav2", "训练家（sav2）"), ("sav1", "同行宝可梦、包包、标记（sav1）")),
                when=SAVE_DUMP),
          Field("--dump-size", "字节数", "number", default="64", group="存档转储", when=SAVE_DUMP),
          Field("--resident", "钩子", "choice", default="turbo", when=HOOK, choices=(
              ("turbo", "加速"), ("shiny", "异色遭遇"), ("ivs", "在画面上显示个体值"),
              ("noencounter", "不遇到野生宝可梦"))),
          Field("--write-unsafe", "允许写入", "switch", default=False, when=HOOK,
                help="钩子会改变运行中的游戏，直到软重启。详见文档中的游戏机代码。"),
          Field(("--version", "--expect-console"), "版本", "choice", default="firered",
                choices=VERSIONS, group="游戏机"),
          Field("--language", "语言", "choice", default="english", choices=LANGUAGES, group="游戏机")),
         fixed=("--live", "--dump-file", "{received}/frlg-dump-{stamp}.bin"), doc="frlg_rom.md"),
))

LGPE_STEPS = "按 X，选择交流、本地交流、交换，输入相同的连接暗号，然后搜索。"

LGPE = Game("lgpe", "精灵宝可梦 Let's Go! 皮卡丘／伊布", "LGPE", "lgpe.md", (
    Tool("lgpe-host", "交换", "bin/lgpe_host.py",
         "使用连接暗号创建交换，游戏机加入。",
         ("先启动主机。", LGPE_STEPS, "选择宝可梦并确认。"),
         (offer("--offer"),
          Field("--code", "连接暗号", default="pikachu,pikachu,pikachu",
                help="用逗号分隔三个图案名称或 0～9 的编号。"),
          FRESH_PID,
          Field("--seconds", "秒数", "number", default="600")),
         fixed=("--first", "echo"), doc="lgpe.md"),
    Tool("lgpe-join", "交换（游戏机创建）", "bin/lgpe_join.py",
         "加入游戏机的交换搜索。",
         ("启动加入程序，最多扫描五分钟。", LGPE_STEPS,
          "出现 PkCamp 后选择宝可梦并确认。"),
         (offer("--offer"), FRESH_PID),
         fixed=("--channels", "1,6,11", "--dwell", "2.5", "--connect", "--connect-seconds", "900",
                "--ack-peer-clock", "--ack-re-announce", "--facts", "lgpe_net_facts.json"),
         doc="lgpe_session.md"),
))

SWSH = Game("swsh", "宝可梦 剑／盾", "SwSh", "swsh.md", (
    Tool("swsh-gift", "神秘礼物", "bin/swsh_gift_host.py",
         "广播神秘卡片；游戏机直接通过无线信号读取，无需加入房间。",
         ("选择神秘礼物、接收礼物、通过本地无线接收。",
          "启动主机；卡片通常会在几秒内出现。",
          "接收卡片后停止主机。"),
         (Field("--species", "宝可梦种类", "species", default="25", group="宝可梦"),
          Field("--level", "等级", "number", default="25", group="宝可梦", help="填 0 由游戏决定等级。"),
          Field("--move1", "招式 1", "move", default="84", group="招式"),
          Field("--move2", "招式 2", "move", default="45", group="招式"),
          Field("--move3", "招式 3", "move", default="86", group="招式"),
          Field("--move4", "招式 4", "move", default="98", group="招式"),
          Field("--set", "携带道具", "item", template="held_item={}", group="其他"),
          Field("--set", "精灵球", "ball", template="ball={}", group="其他"),
          Field("--set", "异色", "switch", template="shiny_type=2", default=False),
          Field("--nickname", "昵称", default="PKCAMP", group="名称"),
          Field("--ot", "初训家", default="POKELDN", group="名称"),
          Field("--set", "其他字段", "multi",
                help="其他记录字段，以空格分隔的 NAME=VALUE 格式输入，例如 nature=10 gender=1 iv_hp=31。",
                limits=(("held_item", 1607, "《剑／盾》中不存在编号超过 1607 的道具；更高的编号会导致包包画面崩溃。"),)),
          Field("--card-id", "卡片 ID", "number", default="9999",
                help="如果游戏机已经持有这张卡片，请更改 ID。"),
          Field("--record", "或发送 .wc8 文件", "file", exts=("wc8",)),
          Field("--seconds", "秒数", "number", default="300")),
         fixed=("--no-validate",), doc="swsh_gift.md"),
    Tool("swsh-join", "交换", "bin/swsh_connect.py", "加入游戏机的连接交换搜索。",
         ("打开 Y 通信，选择连接交换、本地交流、不设暗号；两次提示均按 A。",
          "游戏机搜索期间启动加入程序。",
          "交换画面出现 PkCamp 后选择宝可梦并确认。"),
         (offer("--offer-file", required=False,
                help="选择宝可梦种类，由 PKHeX 生成合法宝可梦。留空则返还队伍首位宝可梦，并改名为 PKCAMP。"),
          Field("--hold", "秒数", "number", default="240")),
         fixed=("--preset", "trade", "--send-snapshot", "live",
                "--save-offered", "{received}/swsh-{stamp}.pk8"),
         doc="swsh_trade.md"),
    Tool("swsh-host", "交换（pokeldn 创建）", "bin/swsh_host.py", "创建连接交换，等待游戏机加入。",
         ("启动主机并等待网络就绪。",
          "打开 Y 通信，选择连接交换、本地交流；两次提示均按 A，然后在野外等待。",
          "出现 PkCamp 后选择宝可梦并确认。"),
         (offer("--offer-file"), FRESH_PID,
          Field("--code", "连接暗号", help="八位数字；留空表示不设暗号。"),
          Field("--channel", "信道", "choice", default="6", choices=CHANNELS),
          Field("--seconds", "秒数", "number", default="900")),
         fixed=("--player-name", "{ot}", "--trainer-name", "{ot}",
                "--trainer-tid", "{tid}", "--trainer-sid", "{sid}",
                "--received", "{received}/swsh-{stamp}.pk8"), doc="swsh_trade.md"),
))

BDSP_ROOM = "宝可梦中心 2 楼，左侧接待员，选择普通的是（不设密码，也不选群组）"

BDSP = Game("bdsp", "宝可梦 晶灿钻石／明亮珍珠", "BDSP", "bdsp.md", (
    Tool("bdsp-join", "交换", "bin/bdsp_connect.py",
         "以角色身份加入游戏机的联合厅并交换。",
         (f"{BDSP_ROOM}。进入房间后远离墙壁等待。",
          "启动加入程序，等待角色出现并走到位。",
          "按 Y，选择交流、交换宝可梦，然后等待自动出现的问候。",
          "每次运行后退出房间，再重新进入。"),
         (offer("--trade-template"),
          Field("--trade-nickname", "昵称", default="PKCAMP"),
          FRESH_PID,
          Field("--hold", "秒数", "number", default="600")),
         fixed=("--channels", "1,6,11", "--count", "9", "--connect", "5", "--join", "6",
                "--reliable-ack", "--reliable-sweep", "3", "--room-walk", "15", "--room-pattern", "fixed",
                "--room-walk-steps", "8", "--join-avatar", "0", "--answer-requests", "--state", "0",
                "--recruiting", "0", "--answer-talk", "--can-talk", "0", "--initiate-talk",
                "--initiate-delay", "3", "--after-approach", "0x06:0001000000", "--trade-reply",
                "--complete-trade", "--src-var", "{src_var}",
                "--trade-save-poke", "{received}/bdsp-{stamp}.pb8"),
         doc="bdsp_trade.md"),
    Tool("bdsp-host", "交换（pokeldn 创建）", "bin/bdsp_host.py",
         "创建联合厅，等待游戏机进入。",
         ("玩家进入房间前先启动主机。",
          f"{BDSP_ROOM}。之后会出现我们的角色。",
          "按 Y，选择交流、交换宝可梦；接受问候后选择宝可梦并确认。"),
         (offer("--offer"),
          FRESH_PID,
          Field("--password", "房间密码", help="八位数字；留空表示普通房间。"),
          Field("--seconds", "秒数", "number", default="1500")),
         fixed=("--ldn-protocol", "1", "--complete-trade", "--save-theirs", "{received}/bdsp-{stamp}"),
         doc="bdsp_trade.md"),
))

PLA_STEPS = ("在祝庆村与交换 NPC 对话，选择交换、本地交流，并确认提示。",
             "输入相同的八位暗号，按 + 开始搜索。")
PLA_OFFER_HELP = "选择宝可梦种类，由 PKHeX 生成合法宝可梦。留空则交换 pokeldn 自带的亚克诺姆。"

PLA = Game("pla", "宝可梦传说 阿尔宙斯", "PLA", "pla.md", (
    Tool("pla-host", "交换", "bin/pla_host.py",
         "使用连接暗号创建交换，游戏机加入。",
         ("先启动主机。", *PLA_STEPS, "选择宝可梦并确认。",
          "保持主机运行到交换结束；中断交换会使交换功能暂时锁定。"),
         (offer("--trade-box-record", required=False, help=PLA_OFFER_HELP),
          Field("--code", "连接暗号", default="00000000"),
          Field("--seconds", "秒数", "number", default="300")),
         fixed=("--channel", "6", "--session-update", "--sustain", "--clock", "--data-exchange",
                "--game-channel", "--trade-box", "--trade-box-collect", "{received}/pla-{stamp}"),
         doc="pla.md"),
    Tool("pla-join", "交换（游戏机创建）", "bin/pla_join.py",
         "加入游戏机的搜索；游戏机会将主机角色交给 pokeldn，加入程序会自动接管。",
         (*PLA_STEPS, "启动加入程序。", "出现交换对象后选择宝可梦并确认。"),
         (offer("--offer", required=False, help=PLA_OFFER_HELP),
          Field("--code", "连接暗号", default="00000000"),
          FRESH_PID),
         fixed=("--offer-out", "{received}/pla-{stamp}.pa8"), doc="pla.md"),
))

SV_SEARCH = "按 X，选择宝可入口、连接交换，保持离线状态，然后搜索。"

SV = Game("sv", "宝可梦 朱／紫", "SV", "sv.md", (
    Tool("sv-join", "交换", "bin/sv_join.py",
         "加入游戏机的连接交换搜索。",
         (SV_SEARCH, "启动加入程序。", "在交换画面选择宝可梦并确认。",
          "若游戏机持续拒绝连接，请退出搜索画面后重新进入。"),
         (offer("--trade-offer"),
          Field("--code", "连接暗号", help="留空则加入不设暗号的搜索。"),
          FRESH_PID),
         fixed=("--phy", "auto", "--seconds", "1500", "--hold", "900", "--channels", "1,6,11",
                "--dwell", "0.4", "--connect-timeout", "6", "--open-delay", "0.3", "--record-delay", "0.3",
                "--session-join", "--answer-migration", "--net-ack", "--ack-flags", "0x00",
                "--game-channel", "--announce-timeout", "20", "--rtt-delay", "0.3",
                "--offer-out", "{received}/sv-{stamp}.hex"), doc="sv.md"),
    Tool("sv-host", "交换（pokeldn 创建）", "bin/sv_host.py",
         "创建交换，等待搜索中的游戏机加入。",
         ("先启动主机。", SV_SEARCH, "在交换画面选择宝可梦并确认。"),
         (offer("--trade-offer"),
          Field("--code", "连接暗号", help="留空则创建不设暗号的搜索。",
                unset=("--game-data",
                       "000000000000000000000000000000000000000000000000000000000000000000648cf400000000")),
          FRESH_PID),
         fixed=("--channel", "6", "--seconds", "900", "--host-player-id", "00000000000000010000000000000000",
                "--player-name", "RyuPlayer", "--rtt-probe", "--net-property", "--clock", "--net-stations", "4",
                "--scarlet-response", "--join-seq", "0", "--update-first-seq", "0", "--update-seq", "1",
                "--session-flags", "0x00", "--no-session-ack", "--update-delay", "2.03",
                "--host-player-name", " ", "--record-delay", "0.17",
                "--send-at", "0.06:0x7c:1:b90104b902b9027b0001b902b902320201b902b902320101b902b902320301",
                "--send-at", "0.06:0x81:1:0000000000f38800000000",
                "--send-at", "0.04:0x81:5:000500000ff00800000000",
                "--announce", "--announce-delay", "5.25",
                "--send-at", "6.00:0x7c:1:b90101b902b90280800001", "--offer-after-open", "2",
                "--offer-out", "{received}/sv-{stamp}.hex"),
         doc="sv.md"),
))

ZA = Game("za", "宝可梦传说 Z-A", "PLZA", "za.md", (
    Tool("za-join", "交换", "bin/za_join.py",
         "加入游戏机的连接交换搜索。",
         ("选择连接交换、本地交流，使用连接暗号搜索。",
          "启动加入程序。建立连接时出现拒绝属正常情况，请保持运行。",
          "交换盒出现 PKLDN 后选择宝可梦并确认。"),
         (offer("--trade-offer"),
          Field("--code", "连接暗号", default="00000000"),
          FRESH_PID),
         fixed=("--channels", "1,6,11", "--dwell", "0.35", "--seconds", "900", "--hold", "450",
                "--quiet-seat", "25", "--connect-timeout", "6", "--mac", "02:11:32:54:76:98", "--game",
                "--offer-delay", "4"),
         doc="za.md"),
    Tool("za-host", "交换（pokeldn 创建）", "bin/za_host.py",
         "创建交换，等待搜索中的游戏机加入。",
         ("先启动主机。",
          "按 X，选择连接游玩、连接交换、附近的玩家，输入相同暗号，然后搜索。",
          "在交换盒选择宝可梦，提出交换并确认。"),
         (offer("--trade-offer"),
          Field("--code", "连接暗号", default="00000000"),
          FRESH_PID,
          Field("--seconds", "秒数", "number", default="900")),
         fixed=("--offer-out", "{received}/za-{stamp}.hex"), doc="za.md"),
))

GAMES = (FRLG, LGPE, SWSH, BDSP, PLA, SV, ZA)
