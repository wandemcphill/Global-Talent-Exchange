"""A5 front-and-back introduction flyer for print at 300 dpi."""

from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "marketing_ads"
PORTRAITS = ROOT / "frontend/react-shell/public/img/portraits"
FACEBANK = ROOT / "backend/generated_media/regen_newgen_faces/new_styles/African"
SRC = OUT / "flyer_src"

# A5 trim, 300 dpi. 148 x 210 mm.
W, H = 1748, 2480
MARGIN = 78

BG = (7, 11, 17)
PANEL = (14, 22, 34)
EMERALD = (54, 227, 138)
GOLD = (245, 197, 24)
WHITE = (244, 246, 250)
MUTED = (168, 180, 198)
LINE = (42, 58, 74)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)


F_BLACK = lambda size: font("ariblk.ttf", size)
F_BOLD = lambda size: font("arialbd.ttf", size)
F_REG = lambda size: font("arial.ttf", size)
F_NAIRA = lambda size: font("segoeuib.ttf", size)


def gradient() -> Image.Image:
    column = Image.new("RGB", (1, H), BG)
    pixels = column.load()
    for y in range(H):
        shade = 8 + int(10 * (1 - abs(y / H - 0.28)))
        pixels[0, y] = (shade, shade + 5, shade + 12)
    return column.resize((W, H), Image.Resampling.BILINEAR)


def wrap(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = word if not current else f"{current} {word}"
        if draw.textlength(trial, font=face) <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_lines(draw, lines, xy, face, fill, gap) -> int:
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=face, fill=fill)
        y += face.size + gap
    return y


def square_crop(image: Image.Image, box=None) -> Image.Image:
    image = image.convert("RGB")
    if box:
        image = image.crop(box)
    width, height = image.size
    side = min(width, height)
    left = max(0, (width - side) // 2)
    top = max(0, (height - side) // 5)
    return image.crop((left, top, left + side, top + side))


def paste_circle(canvas: Image.Image, photo: Image.Image, center, diameter: int, ring) -> None:
    photo = photo.resize((diameter, diameter), Image.Resampling.LANCZOS)
    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse((1, 1, diameter - 2, diameter - 2), fill=255)
    x = int(center[0] - diameter / 2)
    y = int(center[1] - diameter / 2)
    draw = ImageDraw.Draw(canvas)
    pad = 7
    draw.ellipse((x - pad, y - pad, x + diameter + pad, y + diameter + pad), outline=ring, width=5)
    canvas.paste(photo, (x, y), mask)


def load_faces() -> list[tuple[str, str, Image.Image]]:
    osimhen = Image.open(SRC / "osimhen_crop.jpg")
    ow, oh = osimhen.size
    regen = regens()
    return [
        ("Jay-Jay Okocha", "Legend", square_crop(Image.open(PORTRAITS / "legends/jay-jay-okocha-legend.png"))),
        ("Ronaldo de Lima", "Legend", square_crop(Image.open(PORTRAITS / "707715.png"))),
        ("Lamine Yamal", "Active", square_crop(Image.open(SRC / "yamal_head.jpg"))),
        ("Victor Osimhen", "Active", square_crop(osimhen, (int(ow * 0.36), 0, int(ow * 0.64), int(oh * 0.16)))),
        ("Academy player", "Academy", regen[0]),
        ("Academy player", "Academy", regen[1]),
    ]


def regens() -> list[Image.Image]:
    return [
        square_crop(Image.open(FACEBANK / "700.png")),
        square_crop(Image.open(FACEBANK / "710.png")),
    ]


def build_front(people) -> Image.Image:
    canvas = gradient()
    draw = ImageDraw.Draw(canvas)
    draw_site_logo(canvas, (MARGIN, 42))

    pill = "WWW.PLAYGTEX.APP"
    pill_font = F_BOLD(26)
    pill_w = draw.textlength(pill, font=pill_font) + 44
    pill_box = (W - MARGIN - pill_w, 62, W - MARGIN, 112)
    draw.rounded_rectangle(pill_box, radius=25, fill=GOLD)
    draw.text((pill_box[0] + 22, 74), pill, font=pill_font, fill=(12, 16, 22))

    y = 168
    draw.text((MARGIN, y), "BUY AND SELL", font=F_BLACK(78), fill=WHITE)
    draw.text((MARGIN, y + 84), "FOOTBALL PLAYERS", font=F_BLACK(78), fill=EMERALD)
    y = 360
    y = draw_lines(
        draw,
        wrap(draw, "On GTEX you sign players onto your club and sell them on the market.", F_REG(32), W - MARGIN * 2),
        (MARGIN, y),
        F_REG(32),
        MUTED,
        6,
    )

    box_top = y + 22
    box_bottom = box_top + 210
    draw.rounded_rectangle((MARGIN, box_top, W - MARGIN, box_bottom), radius=22, fill=PANEL, outline=GOLD, width=3)
    draw.text((MARGIN + 36, box_top + 22), "FIRST 500 CLUB OWNERS GET", font=F_BOLD(28), fill=GOLD)
    draw.text((MARGIN + 36, box_top + 68), "2,500 GTEX COIN", font=F_BLACK(58), fill=WHITE)
    draw.text((MARGIN + 36, box_top + 138), "+  1,000 FAN COIN", font=F_BLACK(48), fill=EMERALD)

    y = box_bottom + 28
    draw.text((MARGIN, y), "SIGN LEGENDS, ACTIVE STARS, AND ACADEMY PLAYERS", font=F_BOLD(26), fill=GOLD)
    y += 46
    columns = 3
    gap = 30
    usable = W - MARGIN * 2
    cell = (usable - gap * (columns - 1)) // columns
    footer_top = H - 280
    row_pitch = (footer_top - y) // 2
    face = min(cell - 16, row_pitch - 84)
    ring = {"Legend": EMERALD, "Active": GOLD, "Academy": (120, 190, 255)}
    for index, (name, tag, photo) in enumerate(people):
        col = index % columns
        row = index // columns
        cx = MARGIN + col * (cell + gap) + cell // 2
        cy = y + row * row_pitch + face // 2
        paste_circle(canvas, photo, (cx, cy), face, ring[tag])
        label = name.upper()
        name_font = F_BOLD(24)
        while draw.textlength(label, font=name_font) > cell - 8 and name_font.size > 16:
            name_font = F_BOLD(name_font.size - 1)
        nw = draw.textlength(label, font=name_font)
        draw.text((cx - nw / 2, cy + face // 2 + 16), label, font=name_font, fill=WHITE)
        tag_font = F_BOLD(18)
        tw = draw.textlength(tag.upper(), font=tag_font)
        draw.text((cx - tw / 2, cy + face // 2 + 46), tag.upper(), font=tag_font, fill=ring[tag])

    footer_y = H - 250
    draw.rounded_rectangle(
        (MARGIN, footer_y, W - MARGIN, H - 40), radius=18, fill=(10, 18, 28), outline=EMERALD, width=3
    )
    qr_img = make_qr(190)
    canvas.paste(qr_img, (MARGIN + 18, footer_y + 16))
    draw.text((MARGIN + 230, footer_y + 22), "QR CODE", font=F_BOLD(22), fill=EMERALD)
    draw.text((MARGIN + 230, footer_y + 54), "www.playgtex.app", font=F_BLACK(40), fill=WHITE)
    footer = "Play friends. Host a cup. Win up to ₦1,000,000."
    draw.text((MARGIN + 230, footer_y + 112), footer, font=F_NAIRA(26), fill=MUTED)
    return canvas


def draw_site_logo(canvas: Image.Image, origin) -> None:
    """Public site header: condensed GTEX wordmark plus the gold 2027 badge."""
    x, y = origin
    draw = ImageDraw.Draw(canvas)
    word = ImageFont.truetype(str(ROOT / "frontend/assets/fonts/BarlowCondensed-Bold.ttf"), 72)
    badge_font = ImageFont.truetype(str(ROOT / "frontend/assets/fonts/BarlowCondensed-Bold.ttf"), 32)
    cursor = x
    tracking = 10
    for char in "GTEX":
        draw.text((cursor, y), char, font=word, fill=(242, 244, 248))
        cursor += draw.textlength(char, font=word) + tracking
    label = "2027"
    label_w = draw.textlength(label, font=badge_font)
    bx = cursor + 18
    by = y + 18
    draw.rounded_rectangle((bx, by, bx + label_w + 28, by + 42), radius=4, outline=(212, 175, 55), width=2)
    draw.text((bx + 14, by + 2), label, font=badge_font, fill=(212, 175, 55))


def make_qr(size: int) -> Image.Image:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=14, border=2)
    qr.add_data("https://playgtex.app")
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return image.resize((size, size), Image.Resampling.NEAREST)


def section(draw, y, title, body, title_fill=WHITE, body_face=None) -> int:
    body_face = body_face or F_REG(32)
    lines = wrap(draw, body, body_face, W - MARGIN * 2 - 56)
    height = 78 + len(lines) * (body_face.size + 10) + 20
    draw.rounded_rectangle((MARGIN, y, W - MARGIN, y + height), radius=16, fill=PANEL, outline=LINE, width=2)
    draw.text((MARGIN + 26, y + 16), title, font=F_BLACK(32), fill=title_fill)
    draw_lines(draw, lines, (MARGIN + 26, y + 62), body_face, (236, 240, 246), 10)
    return y + height + 16


def build_back(_regen_photos) -> Image.Image:
    canvas = gradient()
    draw = ImageDraw.Draw(canvas)
    y = 36
    draw.text((MARGIN, y), "RUN THE CLUB. THEN COMPETE.", font=F_BLACK(40), fill=WHITE)
    y = 92
    y = section(
        draw,
        y,
        "HIRE AND FIRE STAFF",
        "Sign a general manager, a head of youth development, and a first-team manager such as Mikel Arteta or Carlo Ancelotti, plus the rest of the staff. Hire them. Fire them.",
    )
    y = section(
        draw,
        y,
        "BUILD. GIFT. GET GIFTED.",
        "Build club facilities. Receive coin gifts, and gift coins, on GTEX. Both GTEX Coin and Fan Coin. Club owners also earn TV money from matches.",
    )
    y = section(
        draw,
        y,
        "SET UP A COMPETITION",
        "Create it on GTEX, share the pin with your friends, and compete. Host a community cup or a league, or enter a GTEX competition. Entry is free.",
    )
    draw.text((MARGIN, y), "COME FIRST AND WIN UP TO", font=F_BOLD(22), fill=GOLD)
    y += 32
    prizes = [("1ST", "₦1,000,000", GOLD), ("2ND", "₦500,000", EMERALD), ("3RD", "₦200,000", WHITE)]
    gap = 16
    card_w = (W - MARGIN * 2 - gap * 2) // 3
    for index, (place, amount, color) in enumerate(prizes):
        left = MARGIN + index * (card_w + gap)
        draw.rounded_rectangle((left, y, left + card_w, y + 120), radius=14, fill=PANEL, outline=color, width=3)
        place_font = F_BOLD(20)
        pw = draw.textlength(place, font=place_font)
        draw.text((left + (card_w - pw) / 2, y + 14), place, font=place_font, fill=color)
        amount_font = F_NAIRA(34)
        while draw.textlength(amount, font=amount_font) > card_w - 16:
            amount_font = F_NAIRA(amount_font.size - 1)
        aw = draw.textlength(amount, font=amount_font)
        draw.text((left + (card_w - aw) / 2, y + 56), amount, font=amount_font, fill=WHITE)
    y += 132
    draw.text((MARGIN, y), "Terms and conditions apply.", font=F_REG(22), fill=MUTED)
    y += 32
    trader = (
        "GTEX sells 1 GTEX Coin for ₦60 through Paystack and Korapay, and sells that same coin to coin traders for ₦50. "
        "1 Fan Coin is ₦4 through those gateways, and ₦2.50 to traders. "
        "Traders choose the price they sell at, and the price they pay when they buy coins back. Both GTEX Coin and Fan Coin."
    )
    y = section(draw, y, "COIN TRADERS", trader, title_fill=EMERALD, body_face=F_NAIRA(30))
    draw.text((MARGIN, y), "Terms and conditions apply.", font=F_BOLD(24), fill=GOLD)
    y += 48
    y = section(
        draw,
        y,
        "10% ON THE FIRST DEPOSIT",
        "Register with a referral code, or through a shared link, and get a 10% bonus on your first deposit. Refer someone and you earn 10% of their first deposit in GTEX Coin, paid into your balance. Creators earn 25%. The person they refer still gets 10%. Withdraw the coin, or sell it to a coin trader. Terms and conditions apply.",
        title_fill=GOLD,
    )

    bar_top = H - 430
    draw.rounded_rectangle(
        (MARGIN, bar_top, W - MARGIN, H - 36), radius=18, fill=(10, 18, 28), outline=EMERALD, width=4
    )
    qr_img = make_qr(300)
    canvas.paste(qr_img, (MARGIN + 22, bar_top + 28))
    draw.text((MARGIN + 350, bar_top + 28), "SCAN THIS QR CODE", font=F_BOLD(26), fill=EMERALD)
    draw.text((MARGIN + 350, bar_top + 68), "www.playgtex.app", font=F_BLACK(40), fill=WHITE)
    draw.text((MARGIN + 350, bar_top + 130), "WhatsApp", font=F_BOLD(22), fill=EMERALD)
    draw.text((MARGIN + 350, bar_top + 158), "+2348069938718", font=F_BLACK(32), fill=WHITE)
    draw.text((MARGIN + 350, bar_top + 214), "Email", font=F_BOLD(22), fill=EMERALD)
    draw.text((MARGIN + 350, bar_top + 242), "omotundeoni@playgtex.app", font=F_BOLD(26), fill=WHITE)
    return canvas


def main() -> None:
    people = load_faces()
    front = build_front(people)
    back = build_back(None)
    front_path = OUT / "GTEX-half-flyer-front.png"
    back_path = OUT / "GTEX-half-flyer-back.png"
    pdf_path = OUT / "GTEX-half-flyer-A5.pdf"
    front.save(front_path, dpi=(300, 300))
    back.save(back_path, dpi=(300, 300))
    front.convert("RGB").save(pdf_path, save_all=True, append_images=[back.convert("RGB")], resolution=300)
    print(front_path)
    print(back_path)
    print(pdf_path)


if __name__ == "__main__":
    main()
