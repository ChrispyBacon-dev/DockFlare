import re
import random
from uuid import uuid4

WORDS = [
    "able", "acorn", "acre", "aged", "agile", "airy", "alba", "alert", "aloe", "alto",
    "amber", "ample", "anchor", "arid", "ariel", "arrow", "aspen", "atlas", "azure", "baron",
    "basil", "beam", "bear", "beech", "birch", "blade", "bloom", "blue", "bold", "boon",
    "brake", "brave", "briar", "bridge", "bright", "brisk", "brook", "brush", "bulk", "buoy",
    "calm", "cape", "cedar", "chalk", "chase", "chime", "chip", "chord", "civic", "clamp",
    "clan", "claro", "clean", "clear", "cliff", "cloud", "clove", "coast", "comet", "coral",
    "crest", "crisp", "crop", "cross", "crust", "curl", "curve", "damp", "dawn", "deep",
    "delta", "dense", "depot", "dew", "dome", "door", "dove", "draft", "dune", "dust",
    "eagle", "echo", "edge", "elder", "elm", "ember", "epoch", "equal", "ever", "fable",
    "fair", "fawn", "fern", "field", "film", "fine", "fire", "firm", "fixed", "flag",
    "flame", "flare", "flat", "fleet", "flint", "float", "flood", "floor", "flow", "foam",
    "fond", "ford", "forge", "form", "forte", "frame", "frank", "free", "fresh", "frost",
    "full", "gale", "game", "gate", "gaze", "gear", "gild", "glade", "glare", "glow",
    "gold", "grade", "grain", "grand", "grant", "grape", "grass", "gravel", "gray", "green",
    "grove", "guide", "gulf", "hale", "halt", "haven", "hazel", "helm", "hill", "hive",
    "hold", "holly", "honor", "hope", "horn", "hull", "hunt", "inlet", "iron", "isle",
    "jade", "jasper", "jest", "jewel", "joint", "jump", "keen", "kelp", "kind", "king",
    "kite", "lake", "lance", "lark", "laser", "leaf", "lean", "ledge", "level", "light",
    "lime", "link", "lion", "loch", "lodge", "loft", "loom", "loop", "lore", "lotus",
    "lunar", "mace", "maple", "marsh", "mast", "meadow", "mesa", "mild", "mint", "mist",
    "moat", "mode", "moon", "moor", "moss", "mount", "mural", "naval", "noble", "noon",
    "north", "nova", "oaken", "ocean", "olive", "onyx", "open", "orbit", "otter", "ozone",
    "pact", "pale", "palm", "panel", "patch", "path", "peak", "pearl", "pine", "plain",
    "plank", "plant", "plate", "plaza", "plum", "polar", "pond", "pool", "port", "prime",
    "prism", "proof", "pure", "quail", "quartz", "quest", "quiet", "rail", "rain", "ramp",
    "range", "rapid", "raven", "realm", "reed", "reef", "reign", "ridge", "rift", "rigid",
    "ring", "river", "road", "robin", "rock", "rouge", "round", "route", "ruby", "rune",
    "rush", "sage", "sail", "salt", "sand", "satin", "scale", "scope", "scout", "seal",
    "shelf", "shim", "shore", "sigil", "silk", "silver", "skiff", "slate", "slick", "slope",
    "solar", "solid", "sonic", "span", "spark", "speed", "spire", "spray", "sprint", "spur",
    "stark", "star", "steam", "steel", "stern", "still", "stone", "storm", "strand", "stream",
    "stripe", "strong", "strut", "sunlit", "swift", "talon", "teal", "terra", "test", "tide",
    "timber", "titan", "tonal", "torch", "tower", "trace", "trail", "tram", "trend", "trove",
    "trunk", "tulip", "tuned", "ultra", "unity", "valid", "valor", "vault", "veil", "venom",
    "virid", "vivid", "vocal", "void", "ward", "wave", "weld", "wheat", "white", "wild",
    "willow", "wind", "wing", "winter", "wisp", "wren", "yard", "zeal", "zenith", "zinc",
]

_ADDRESS_RE = re.compile(r'^[a-zA-Z0-9._+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


def validate_alias_address(address):
    if not address or not isinstance(address, str):
        return False, "address required"
    if not _ADDRESS_RE.match(address):
        return False, "invalid address format"
    local, _, domain = address.partition('@')
    if not local or not domain:
        return False, "invalid address format"
    if '..' in address:
        return False, "invalid address format"
    return True, None


def generate_alias(domain, style="word-word-num", db=None, max_attempts=20):
    for _ in range(max_attempts):
        if style == "word-word-num":
            candidate = f"{random.choice(WORDS)}.{random.choice(WORDS)}.{random.randint(100, 999)}@{domain}"
        elif style == "word-num":
            candidate = f"{random.choice(WORDS)}.{random.randint(1000, 9999)}@{domain}"
        else:
            candidate = f"{uuid4().hex[:10]}@{domain}"

        if db is None or not _address_exists(db, candidate):
            return candidate

    return f"{uuid4().hex[:10]}@{domain}"


def _address_exists(db, address):
    if db.execute("SELECT 1 FROM aliases WHERE address=?", (address,)).fetchone():
        return True
    if db.execute("SELECT 1 FROM mailboxes WHERE address=?", (address,)).fetchone():
        return True
    return False
