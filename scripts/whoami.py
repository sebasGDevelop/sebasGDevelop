import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quest_log import ASSETS, CREAM, CYAN, RED, AMBER, DIM, F, crt, fit, panel  # noqa: E402

# ------------------------------------------------------------ edit me
PLAYER = "PLAYER 1 · SEBAS"
LEVEL = "LV. 01"
HP, XP = 10, 9  
ATTRIBUTES = [
    ("CLASS", "Systems Engineering Student"),
    ("BRANCH", "Game Development"),
    ("ALIGNMENT", "Logic by day, pixels by night"),
]
INVENTORY = ["C#", "C++", "Unity", "Godot", "Python"]
QUESTS = [
    ("MAIN QUEST", "Medieval Market"),
    ("SIDE QUEST", "Personal Growth App"),
    ("POWER-UP", "coffee + lofi"),
]
DIALOG = "A wild developer appeared! What will you do?"
OPTIONS = ["VIEW PROJECTS", "CONTACT", "INVITE TO PARTY", "RUN"]
# --------------------------------------------------------------------

GREEN = (142, 242, 90)
SLOT_BG = (26, 20, 56)


def bar(d, x0, y, x1, filled, color, label):
    """Segmented pixel bar, like an old RPG HUD."""
    d.text((x0, y - 6), label, font=F, fill=DIM)
    bx0, h, gap, n = x0 + 56, 20, 6, 10
    seg = (x1 - bx0 - gap * (n - 1)) / n
    for i in range(n):
        sx = bx0 + i * (seg + gap)
        d.rectangle((sx, y, sx + seg, y + h), fill=color if i < filled else (40, 36, 60))
        if i < filled:  # small highlight on top of each segment
            d.rectangle((sx, y, sx + seg, y + 4), fill=tuple(min(255, c + 60) for c in color))


def row(d, L, R, y, label, value, color=CREAM):
    d.text((L, y), label, font=F, fill=DIM)
    lw = d.textlength(label, font=F)
    value = fit(d, value, R - L - lw - 32)
    d.text((R - d.textlength(value, font=F), y), value, font=F, fill=color)


def whoami(bg):
    bg = bg.copy()
    bg.paste(bg.crop((100, 8, 140, 54)), (210, 8))  
    img = bg.resize((bg.width * 4, bg.height * 4), Image.NEAREST)
    box = (48, 52, img.width - 48, img.height - 22)
    img, d = panel(img, box, " whoami.sav ")
    L, R = box[0] + 36, box[2] - 36

    # portrait: the SGD icon inside a pixel frame
    px, py, ps = L, box[1] + 34, 160
    d.rectangle((px - 6, py - 6, px + ps + 5, py + ps + 5), fill=SLOT_BG, outline=CREAM, width=4)
    icon = Image.open(os.path.join(ASSETS, "sgd-icon.png")).convert("RGB").resize((ps, ps), Image.LANCZOS)
    img.paste(icon, (px, py))
    d = ImageDraw.Draw(img)
    d.fontmode = "1"

    # header next to the portrait
    hx = px + ps + 40
    d.text((hx, py + 4), PLAYER, font=F, fill=CREAM)
    d.text((R - d.textlength(LEVEL, font=F), py + 4), LEVEL, font=F, fill=AMBER)
    bar(d, hx, py + 62, R, HP, RED, "HP")
    bar(d, hx, py + 102, R, XP, CYAN, "XP")
    status = "● ONLINE"
    d.text((hx, py + 132), status, font=F, fill=GREEN)

    # attributes
    y = py + ps + 22
    for label, value in ATTRIBUTES:
        row(d, L, R, y, label, value)
        y += 36

    # inventory slots
    y += 4
    d.text((L, y), "INVENTORY", font=F, fill=DIM)
    y += 40
    gap = 16
    sw = (R - L - gap * (len(INVENTORY) - 1)) / len(INVENTORY)
    for i, item in enumerate(INVENTORY):
        sx = L + i * (sw + gap)
        d.rectangle((sx, y, sx + sw, y + 48), fill=SLOT_BG, outline=AMBER, width=3)
        d.text((sx + (sw - d.textlength(item, font=F)) / 2, y + 7), item, font=F, fill=CREAM)

    # quests
    y += 64
    for label, value in QUESTS:
        row(d, L, R, y, label, value, AMBER if label == "MAIN QUEST" else CREAM)
        y += 36

    # battle dialog
    y += 8
    dbox = (L - 12, y, R + 12, y + 96)
    d.rectangle(dbox, fill=(8, 8, 16), outline=CREAM, width=3)
    d.text((L + 8, y + 12), fit(d, DIALOG, R - L - 16), font=F, fill=CREAM)
    ox, oy = L + 8, y + 50
    for i, opt in enumerate(OPTIONS):
        text = ("▶ " if i == 0 else "  ") + opt
        d.text((ox, oy), text, font=F, fill=RED if i == 0 else CREAM)
        ox += d.textlength(text, font=F) + 36
    assert dbox[3] <= box[3] - 12, "content taller than the panel"
    return crt(img, k=0.06)


if __name__ == "__main__":
    bg = Image.open(os.path.join(ASSETS, "quest-bg.png")).convert("RGB")
    whoami(bg).save(os.path.join(ASSETS, "whoami.png"), optimize=True)
    print("assets/whoami.png saved")
