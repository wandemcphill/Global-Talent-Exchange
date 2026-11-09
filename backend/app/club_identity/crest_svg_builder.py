from __future__ import annotations

import html


def render_crest_svg(
    *,
    shape: str = "shield",
    primary_color: str = "#1E3A8A",
    secondary_color: str = "#FFFFFF",
    accent_color: str = "#F59E0B",
    initials: str = "FC",
    icon_family: str = "lion",
    trophy_stars: int = 0,
    style: str = "traditional",  # traditional, modern, metallic
    border_width: int = 6,
) -> str:
    """Generate clean, scalable, standalone SVG vector football crest."""
    safe_primary = html.escape(primary_color)
    safe_secondary = html.escape(secondary_color)
    safe_accent = html.escape(accent_color)
    safe_initials = html.escape(initials[:5].upper())

    # Styling filters and gradients
    defs = []
    if style == "metallic":
        defs.append(f"""
        <linearGradient id="metal_grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="{safe_accent}" stop-opacity="0.9" />
            <stop offset="40%" stop-color="#FFFFFF" stop-opacity="0.8" />
            <stop offset="70%" stop-color="{safe_accent}" stop-opacity="0.95" />
            <stop offset="100%" stop-color="#B45309" stop-opacity="1" />
        </linearGradient>
        <filter id="emboss" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="4" stdDeviation="3" flood-opacity="0.35" />
        </filter>
        """)
    else:
        defs.append("""
        <filter id="soft_shadow" x="-10%" y="-10%" width="120%" height="120%">
            <feDropShadow dx="0" dy="3" stdDeviation="2.5" flood-opacity="0.25" />
        </filter>
        """)

    defs_markup = f"<defs>{''.join(defs)}</defs>"
    filter_attr = 'filter="url(#emboss)"' if style == "metallic" else 'filter="url(#soft_shadow)"'
    border_color = "url(#metal_grad)" if style == "metallic" else safe_accent

    # Badge geometry outlines (viewBox 0 0 200 240)
    shape_norm = shape.lower()
    if shape_norm == "round":
        outer_elem = f'<circle cx="100" cy="115" r="90" fill="{safe_primary}" stroke="{border_color}" stroke-width="{border_width}" {filter_attr}/>'
        inner_elem = f'<circle cx="100" cy="115" r="76" fill="none" stroke="{safe_secondary}" stroke-width="2" stroke-dasharray="4,3"/>'
        bg_shape = f"{outer_elem}{inner_elem}"
        center_y = 105
    elif shape_norm == "diamond":
        path = "M 100,15 L 188,115 L 100,215 L 12,115 Z"
        outer_elem = f'<path d="{path}" fill="{safe_primary}" stroke="{border_color}" stroke-width="{border_width}" stroke-linejoin="round" {filter_attr}/>'
        inner_path = "M 100,28 L 175,115 L 100,202 L 25,115 Z"
        inner_elem = f'<path d="{inner_path}" fill="none" stroke="{safe_secondary}" stroke-width="2"/>'
        bg_shape = f"{outer_elem}{inner_elem}"
        center_y = 115
    elif shape_norm == "pennant":
        path = "M 20,20 L 180,20 L 180,120 L 100,225 L 20,120 Z"
        outer_elem = f'<path d="{path}" fill="{safe_primary}" stroke="{border_color}" stroke-width="{border_width}" stroke-linejoin="round" {filter_attr}/>'
        inner_path = "M 32,32 L 168,32 L 168,116 L 100,208 L 32,116 Z"
        inner_elem = f'<path d="{inner_path}" fill="none" stroke="{safe_secondary}" stroke-width="2"/>'
        bg_shape = f"{outer_elem}{inner_elem}"
        center_y = 100
    else:  # shield (default)
        path = "M 25,25 Q 100,12 175,25 C 175,90 175,145 100,225 C 25,145 25,90 25,25 Z"
        outer_elem = f'<path d="{path}" fill="{safe_primary}" stroke="{border_color}" stroke-width="{border_width}" stroke-linejoin="round" {filter_attr}/>'
        inner_path = "M 36,36 Q 100,26 164,36 C 164,95 164,142 100,210 C 36,142 36,95 36,36 Z"
        inner_elem = f'<path d="{inner_path}" fill="none" stroke="{safe_secondary}" stroke-width="2" opacity="0.8"/>'
        bg_shape = f"{outer_elem}{inner_elem}"
        center_y = 96

    # Inner Icon Element
    icon_norm = icon_family.lower()
    icon_color = safe_accent if style != "metallic" else "url(#metal_grad)"
    if icon_norm == "crown":
        icon_svg = f"""
        <g transform="translate(68, {center_y - 32}) scale(0.65)">
            <path d="M 10,70 L 20,20 L 45,50 L 50,10 L 55,50 L 80,20 L 90,70 Z" fill="{icon_color}" stroke="{safe_secondary}" stroke-width="2" />
            <circle cx="20" cy="18" r="4" fill="{safe_secondary}" />
            <circle cx="50" cy="8" r="5" fill="{safe_secondary}" />
            <circle cx="80" cy="18" r="4" fill="{safe_secondary}" />
            <rect x="10" y="70" width="80" height="12" rx="3" fill="{safe_secondary}" />
            <circle cx="30" cy="76" r="2.5" fill="{safe_primary}" />
            <circle cx="50" cy="76" r="2.5" fill="{safe_accent}" />
            <circle cx="70" cy="76" r="2.5" fill="{safe_primary}" />
        </g>
        """
    elif icon_norm == "eagle":
        icon_svg = f"""
        <g transform="translate(65, {center_y - 35}) scale(0.7)">
            <path d="M 50,5 L 42,22 L 20,15 L 28,38 L 5,35 L 20,58 L 2,65 L 25,82 L 40,80 L 50,95 L 60,80 L 75,82 L 98,65 L 80,58 L 95,35 L 72,38 L 80,15 L 58,22 Z"
                  fill="{icon_color}" stroke="{safe_secondary}" stroke-width="1.8" />
            <circle cx="46" cy="28" r="2.5" fill="{safe_secondary}" />
        </g>
        """
    elif icon_norm == "star":
        icon_svg = f"""
        <g transform="translate(65, {center_y - 35}) scale(0.7)">
            <polygon points="50,5 64,36 98,38 72,62 80,95 50,76 20,95 28,62 2,38 36,36"
                     fill="{icon_color}" stroke="{safe_secondary}" stroke-width="2" />
        </g>
        """
    elif icon_norm == "oak":
        icon_svg = f"""
        <g transform="translate(70, {center_y - 32}) scale(0.6)">
            <path d="M 50,15 C 30,15 25,35 30,50 C 15,55 10,75 25,85 C 35,90 45,95 50,105 C 55,95 65,90 75,85 C 90,75 85,55 70,50 C 75,35 70,15 50,15 Z"
                  fill="{icon_color}" stroke="{safe_secondary}" stroke-width="2" />
            <path d="M 50,15 L 50,95 M 35,50 L 50,65 M 65,50 L 50,65" stroke="{safe_secondary}" stroke-width="2" fill="none" />
        </g>
        """
    elif icon_norm == "bolt":
        icon_svg = f"""
        <g transform="translate(72, {center_y - 35}) scale(0.68)">
            <polygon points="55,0 15,48 42,48 25,95 75,40 48,40"
                     fill="{icon_color}" stroke="{safe_secondary}" stroke-width="2" stroke-linejoin="round" />
        </g>
        """
    elif icon_norm == "ball":
        icon_svg = f"""
        <g transform="translate(68, {center_y - 32}) scale(0.65)">
            <circle cx="50" cy="50" r="44" fill="{safe_secondary}" stroke="{safe_primary}" stroke-width="3" />
            <polygon points="50,30 65,42 60,60 40,60 35,42" fill="{safe_primary}" />
            <line x1="50" y1="30" x2="50" y2="8" stroke="{safe_primary}" stroke-width="2" />
            <line x1="65" y1="42" x2="88" y2="35" stroke="{safe_primary}" stroke-width="2" />
            <line x1="60" y1="60" x2="78" y2="80" stroke="{safe_primary}" stroke-width="2" />
            <line x1="40" y1="60" x2="22" y2="80" stroke="{safe_primary}" stroke-width="2" />
            <line x1="35" y1="42" x2="12" y2="35" stroke="{safe_primary}" stroke-width="2" />
        </g>
        """
    else:  # lion (default)
        icon_svg = f"""
        <g transform="translate(66, {center_y - 35}) scale(0.68)">
            <path d="M 35,20 C 35,10 50,5 60,15 C 65,10 75,12 75,20 C 85,25 85,40 75,50 C 70,60 60,65 50,68 C 45,75 55,90 65,95 L 45,95 C 35,85 30,70 35,55 C 25,48 25,30 35,20 Z"
                  fill="{icon_color}" stroke="{safe_secondary}" stroke-width="2" />
            <circle cx="58" cy="22" r="3" fill="{safe_secondary}" />
            <polygon points="40,5 45,15 35,15" fill="{safe_accent}" />
        </g>
        """

    # Initials Text Box
    text_y = center_y + 48
    initials_svg = f"""
    <g transform="translate(100, {text_y})">
        <rect x="-42" y="-14" width="84" height="26" rx="4" fill="{safe_secondary}" opacity="0.95" />
        <text text-anchor="middle" y="5" font-family="'Inter', 'Montserrat', -apple-system, sans-serif"
              font-size="14" font-weight="900" letter-spacing="2" fill="{safe_primary}">{safe_initials}</text>
    </g>
    """

    # Trophy Stars on top
    stars_svg = ""
    if trophy_stars > 0:
        star_count = min(5, trophy_stars)
        star_items = []
        start_x = 100 - ((star_count - 1) * 12)
        for i in range(star_count):
            sx = start_x + (i * 24)
            star_items.append(
                f'<polygon points="{sx},6 {sx+4},14 {sx+12},15 {sx+6},21 {sx+8},29 {sx},24 {sx-8},29 {sx-6},21 {sx-12},15 {sx-4},14" fill="{safe_accent}" stroke="#FFFFFF" stroke-width="1" />'
            )
        stars_svg = f"<g>{''.join(star_items)}</g>"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 240" width="100%" height="100%">
{defs_markup}
{bg_shape}
{icon_svg}
{initials_svg}
{stars_svg}
</svg>""".strip()
