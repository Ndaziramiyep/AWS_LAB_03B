"""Builds docs/discovery-report.pdf: draw.io-style figures (inline SVG) + report text, printed by headless Chrome.

Run:  python docs/report-src/build_discovery_report.py
"""

import html                                                # Escape text placed inside SVG/HTML
import pathlib                                             # File paths
import subprocess                                          # Run headless Chrome
import sys                                                 # Exit codes

HERE = pathlib.Path(__file__).resolve().parent             # docs/report-src
OUT_HTML = HERE / "discovery-report.html"                  # Intermediate HTML (open it in a browser to preview)
OUT_PDF = HERE.parent / "discovery-report.pdf"             # Final deliverable
CHROME = [                                                 # Browsers that can print to PDF
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

AUTHOR = "Patrick Ndaziramiye"                             # Report author
LAB = "Delivering Order System Updates Safely"             # Lab name
DATE = "November 2026"                                     # Report date

# ----------------------------------------------------------------------------- colours
# AWS architecture-icon category colours, so each service family is recognisable.
C = {
    "compute": "#ED7100",                                  # Compute & containers (orange)
    "network": "#8C4FFF",                                  # Networking (purple)
    "security": "#DD344C",                                 # Security & identity (red)
    "devtools": "#3B48CC",                                 # Developer tools (blue)
    "integration": "#E7157B",                              # App integration & management (pink)
    "storage": "#7AA116",                                  # Storage (green)
    "github": "#24292F",                                   # GitHub (near-black)
    "people": "#1E88E5",                                   # Customers (light blue)
    "gold": "#C79A00",                                     # Warnings / CTO (gold)
    "teal": "#00897B",                                     # Operations (teal)
}

# draw.io's classic fill/stroke pairs (the defaults in its style panel).
DRAWIO = {
    "blue": ("#dae8fc", "#6c8ebf"),                        # Blue
    "green": ("#d5e8d4", "#82b366"),                       # Green
    "yellow": ("#fff2cc", "#d6b656"),                      # Yellow
    "orange": ("#ffe6cc", "#d79b00"),                      # Orange
    "red": ("#f8cecc", "#b85450"),                         # Red
    "purple": ("#e1d5e7", "#9673a6"),                      # Purple
    "grey": ("#f5f5f5", "#666666"),                        # Grey
}

# White line glyphs drawn on a 24x24 grid (original simple pictograms).
G = {
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>',
    "repo": '<circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="7" r="2"/><path d="M6 7v10M18 9v1a4 4 0 0 1-4 4h-4a4 4 0 0 0-4 4"/>',
    "actions": '<circle cx="12" cy="12" r="9"/><path d="M10 8.5l5 3.5-5 3.5z" fill="#fff"/>',
    "ecr": '<rect x="4" y="8" width="16" height="12" rx="1"/><path d="M4 12h16M8 8V4h8v4M9 16h6"/>',
    "eventbridge": '<path d="M3 12h18M7 6h10M7 18h10"/><circle cx="3" cy="12" r="1.5" fill="#fff"/><circle cx="21" cy="12" r="1.5" fill="#fff"/><circle cx="7" cy="6" r="1.5" fill="#fff"/><circle cx="17" cy="18" r="1.5" fill="#fff"/>',
    "pipeline": '<path d="M3 7h11l4 5-4 5H3l4-5z"/><path d="M17 7h2l4 5-4 5h-2"/>',
    "codedeploy": '<path d="M4 8h14M14 4l4 4-4 4M20 16H6M10 12l-4 4 4 4"/>',
    "cloudwatch": '<circle cx="11" cy="11" r="7"/><path d="M16 16l5 5M7 11h2l1-2.5 2 5 1-2.5h2"/>',
    "cfn": '<path d="M12 3l9 4.5-9 4.5-9-4.5z"/><path d="M3 12l9 4.5 9-4.5M3 16.5l9 4.5 9-4.5"/>',
    "iam": '<circle cx="8" cy="12" r="4"/><path d="M12 12h9M18 12v3M21 12v2.5"/>',
    "alb": '<circle cx="12" cy="12" r="3"/><path d="M3 12h6M15 12h6M14.2 9.8L19 5M14.2 14.2L19 19M17 5h2v2M17 19h2v-2M19 11l2 1-2 1"/>',
    "fargate": '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M12 12l8-4.5M12 12v9M12 12L4 7.5"/>',
    "endpoint": '<path d="M9 3v5M15 3v5M7 8h10v3a5 5 0 0 1-10 0zM12 16v5"/>',
    "s3": '<ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6l2 12.5c.3 1.6 2.9 2.5 6 2.5s5.7-.9 6-2.5L20 6"/>',
    "scaling": '<rect x="8" y="8" width="8" height="8" rx="1"/><path d="M3 12h3M18 12h3M12 3v3M12 18v3M4 4l3 3M20 20l-3-3M20 4l-3 3M4 20l3-3"/>',
    "vpc": '<path d="M7 18h10a4 4 0 0 0 .6-7.95A6 6 0 0 0 6.1 11.6 3.3 3.3 0 0 0 7 18z"/>',
    "cloud": '<path d="M7 18h10a4 4 0 0 0 .6-7.95A6 6 0 0 0 6.1 11.6 3.3 3.3 0 0 0 7 18z"/>',
    "warning": '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.4"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 3"/>',
    "unlock": '<rect x="5" y="11" width="14" height="10" rx="1.5"/><path d="M8 11V7a4 4 0 0 1 7.6-1.8M12 15v2"/>',
    "undo": '<path d="M9 14L4 9l5-5M4 9h10a6 6 0 0 1 0 12h-3"/>',
    "frown": '<circle cx="12" cy="12" r="9"/><path d="M8 16.5c2-2 6-2 8 0M9 9.5v.5M15 9.5v.5"/>',
    "drift": '<path d="M4 6h9M4 12h16M4 18h6M16 4l3 2-3 2M13 16l3 2-3 2"/>',
    "money": '<circle cx="12" cy="12" r="9"/><path d="M15 9c-.5-1-1.7-1.5-3-1.5-1.7 0-3 .8-3 2s1.3 1.8 3 2 3 .8 3 2-1.3 2-3 2c-1.3 0-2.5-.5-3-1.5M12 6v1.5M12 16.5V18"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "gear": '<circle cx="12" cy="12" r="3.5"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9L7 7M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
    "star": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
    "cart": '<path d="M3 4h2l2.5 11h11L21 7H6.4"/><circle cx="9" cy="19.5" r="1.3"/><circle cx="17" cy="19.5" r="1.3"/>',
    "script": '<path d="M8 4h11v13a3 3 0 0 1-3 3H6a3 3 0 0 1-3-3v-1h11v1a3 3 0 0 0 3 3M8 4a2 2 0 0 0-2 2v10M11 9h5M11 13h5"/>',
    "terminal": '<rect x="3" y="5" width="18" height="14" rx="1.5"/><path d="M7 10l3 2-3 2M12 15h5"/>',
    "rolling": '<path d="M20 12a8 8 0 0 1-14 5.3M4 12a8 8 0 0 1 14-5.3M18 3v4h-4M6 21v-4h4"/>',
    "bluegreen": '<rect x="3" y="6" width="8" height="12" rx="1"/><rect x="13" y="6" width="8" height="12" rx="1"/><path d="M11 12h2"/>',
    "canary": '<path d="M19 5L5 19"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
    "server": '<rect x="4" y="4" width="16" height="6" rx="1"/><rect x="4" y="14" width="16" height="6" rx="1"/><path d="M7.5 7h.5M7.5 17h.5"/>',
    "sparkle": '<path d="M12 3l2 7 7 2-7 2-2 7-2-7-7-2 7-2z"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    "book": '<path d="M4 19V5a2 2 0 0 1 2-2h14v16H6a2 2 0 0 0-2 2 2 2 0 0 0 2 2h14"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5" fill="#fff"/>',
    "rocket": '<path d="M12 15l-3-3c1.5-5 4.5-8 10-9-1 5.5-4 8.5-9 10z"/><path d="M9 12l-4 1-2 3 4 1M12 15l-1 4 3 2 1-4M15 8.5v.5"/>',
}


def esc(t):
    """Escape text for SVG/HTML."""
    return html.escape(str(t))                             # &, <, > and quotes


def lighten(hex_color, amount=0.35):
    """Mix a colour with white (used for the icon gradient highlight)."""
    h = hex_color.lstrip("#")                              # Drop the #
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))     # Parse RGB
    mix = lambda c: int(c + (255 - c) * amount)            # Move toward white
    return f"#{mix(r):02x}{mix(g):02x}{mix(b):02x}"        # Back to hex


def defs():
    """Shared SVG definitions: arrowheads and one gradient per colour."""
    grads = "".join(                                       # Diagonal gradient per palette colour
        f'<linearGradient id="g{k}" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{lighten(v)}"/><stop offset="1" stop-color="{v}"/></linearGradient>'
        for k, v in C.items()
    )
    return (
        "<defs>"                                           # Definitions block
        '<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0 0L10 5 0 10z" fill="#333"/></marker>'  # draw.io classic block arrow
        '<marker id="arrg" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0 0L10 5 0 10z" fill="#82b366"/></marker>'  # Green arrowhead
        '<marker id="arrr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0 0L10 5 0 10z" fill="#b85450"/></marker>'  # Red arrowhead
        '<linearGradient id="risk" gradientUnits="userSpaceOnUse" x1="12" y1="0" x2="660" y2="0"><stop offset="0" stop-color="#b85450"/>'
        '<stop offset=".5" stop-color="#d6b656"/><stop offset="1" stop-color="#82b366"/></linearGradient>'  # Risk axis
        f"{grads}</defs>"                                  # Icon gradients
    )


def svg(w, h, body):
    """Wrap figure content in an SVG on the draw.io grid canvas."""
    return (f'<svg class="fig" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
            f'font-family="Helvetica, Arial, sans-serif">{defs()}{body}</svg>')


def text(x, y, lines, size=11, weight="normal", anchor="middle", color="#1d1d1d", italic=False):
    """Multi-line text; lines separated by '\\n'. y is the first baseline."""
    parts = str(lines).split("\n")                         # Split into lines
    lh = size * 1.25                                       # Line height
    style = ' font-style="italic"' if italic else ""       # Optional italics
    spans = "".join(                                       # One tspan per line
        f'<tspan x="{x}" dy="{0 if i == 0 else lh}">{esc(p)}</tspan>' for i, p in enumerate(parts)
    )
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
            f'fill="{color}"{style}>{spans}</text>')


def ctext(cx, cy, lines, size=11, weight="normal", color="#1d1d1d", anchor="middle", x=None):
    """Text vertically centred on cy."""
    n = len(str(lines).split("\n"))                        # Line count
    y0 = cy - (n - 1) * size * 1.25 / 2 + size * 0.35      # First baseline so the block is centred
    return text(cx if x is None else x, y0, lines, size, weight, anchor, color)


def icon(kind, cx, cy, s=40, color="devtools", label=None, round_=False, lsize=9.5, lcolor="#1d1d1d"):
    """Coloured icon tile with a white glyph, optional label underneath."""
    x, y = cx - s / 2, cy - s / 2                          # Top-left corner
    shape = (f'<circle cx="{s/2}" cy="{s/2}" r="{s/2}" fill="url(#g{color})"/>' if round_ else
             f'<rect width="{s}" height="{s}" rx="{s*0.14}" fill="url(#g{color})"/>')  # Circle or rounded square
    k = s * 0.62 / 24                                      # Glyph scale
    pad = s * 0.19                                         # Glyph inset
    out = (f'<g transform="translate({x},{y})">{shape}'
           f'<g transform="translate({pad},{pad}) scale({k})" fill="none" stroke="#fff" stroke-width="{1.9 if s > 30 else 2.2}" '
           f'stroke-linecap="round" stroke-linejoin="round">{G[kind]}</g></g>')  # Tile + glyph
    if label:                                              # Optional caption
        out += text(cx, cy + s / 2 + lsize + 2, label, lsize, color=lcolor)
    return out


def icon_html(kind, color, s=26, round_=False):
    """Stand-alone small SVG icon for use inside HTML text (cards, tables)."""
    return (f'<svg width="{s}" height="{s}" viewBox="0 0 {s} {s}" class="ico">{defs()}'
            f'{icon(kind, s/2, s/2, s, color, round_=round_)}</svg>')


def box(x, y, w, h, scheme="blue", lines="", size=10.5, rx=6, dash=False, weight="normal", sw=1, fill=None, stroke=None):
    """draw.io rounded rectangle with centred text."""
    f, s = DRAWIO[scheme]                                  # Palette pair
    f, s = fill or f, stroke or s                          # Allow overrides
    d = ' stroke-dasharray="5 3"' if dash else ""          # Dashed border
    out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{f}" stroke="{s}" stroke-width="{sw}"{d}/>'  # Shape
    if lines:                                              # Optional label
        out += ctext(x + w / 2, y + h / 2, lines, size, weight)
    return out


def arrow(pts, dashed=False, color="#333", marker="arr", label=None, at=None, lsize=9, width=1.2):
    """Orthogonal connector through the given points, with an arrowhead and optional label."""
    d = "M" + " L".join(f"{x} {y}" for x, y in pts)        # Polyline path
    dash = ' stroke-dasharray="5 3"' if dashed else ""     # Dashed style
    out = (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{dash} '
           f'marker-end="url(#{marker})"/>')               # Connector
    if label:                                              # Edge label with white halo, like draw.io
        lx, ly = at or pts[len(pts) // 2]                  # Label position
        out += (f'<text x="{lx}" y="{ly}" font-size="{lsize}" text-anchor="middle" fill="#333" '
                f'stroke="#fff" stroke-width="3" paint-order="stroke">{esc(label)}</text>')
    return out


def badge(n, x, y, fill="#232F3E"):
    """Numbered step marker."""
    return (f'<circle cx="{x}" cy="{y}" r="8.5" fill="{fill}" stroke="#fff" stroke-width="1.5"/>'
            + ctext(x, y, str(n), 9.5, "bold", "#fff"))   # Circle + number


def group(x, y, w, h, label, stroke, kind=None, fill="none", dash=False, color=None, lcolor=None, center=False):
    """AWS-diagram style group (AWS Cloud, VPC, AZ, subnet) with a corner icon and label."""
    d = ' stroke-dasharray="6 4"' if dash else ""          # Dashed border for AZs
    out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="1.3"{d}/>'  # Frame
    if center:                                             # AZ style: centred label
        return out + text(x + w / 2, y + 13, label, 9.5, "bold", "middle", lcolor or stroke)
    tx = x + 6                                             # Label x
    if kind:                                               # Corner icon tile
        out += f'<rect x="{x}" y="{y}" width="20" height="20" fill="{stroke}"/>'  # Solid corner square
        out += (f'<g transform="translate({x+3},{y+3}) scale({14/24})" fill="none" stroke="#fff" stroke-width="2.2" '
                f'stroke-linecap="round" stroke-linejoin="round">{G[kind]}</g>')  # Glyph
        tx = x + 25                                        # Label after icon
    return out + text(tx, y + 14, label, 9.5, "bold", "start", lcolor or stroke)


# ============================================================================ FIGURES

def fig_flow():
    """Figure 1: end-to-end flow of a change (cover)."""
    items = [                                              # (glyph, colour, label)
        ("user", "people", "Developer"), ("repo", "github", "App repo"), ("actions", "github", "GitHub Actions\n(OIDC)"),
        ("ecr", "compute", "Amazon ECR"), ("eventbridge", "integration", "EventBridge"), ("pipeline", "devtools", "CodePipeline"),
        ("codedeploy", "devtools", "CodeDeploy\nblue/green"), ("fargate", "compute", "ECS Fargate\n+ ALB"), ("cart", "people", "Customers"),
    ]
    b = group(6, 12, 218, 112, "GitHub", "#57606a", kind="repo", fill="#fafbfc", dash=True)  # GitHub lane
    b += group(230, 12, 382, 112, "AWS Cloud · eu-west-1", "#232F3E", kind="cloud", fill="#fffdf9")  # AWS lane
    xs = [40 + i * 75 for i in range(len(items))]          # Icon centres
    for i, (k, c, lab) in enumerate(items):                # Draw icons
        b += icon(k, xs[i], 62, 38, c, lab, round_=(k in ("user", "cart")))
    for i in range(len(items) - 1):                        # Connectors + step numbers
        b += arrow([(xs[i] + 22, 62), (xs[i + 1] - 22, 62)])
        b += badge(i + 1, (xs[i] + xs[i + 1]) / 2, 47)
    return svg(680, 132, b)


def fig_approaches():
    """Figure 2: the spectrum of delivery approaches and tooling options."""
    b = '<path d="M12 24 L660 24" stroke="url(#risk)" stroke-width="4"/>'  # Risk axis line
    b += '<path d="M658 18 L670 24 658 30z" fill="#82b366"/>'  # Small arrowhead drawn by hand
    b += text(12, 15, "Higher release risk", 9.5, "bold", "start", "#b85450")  # Axis label left
    b += text(656, 15, "Lower release risk", 9.5, "bold", "end", "#4d7c3a")   # Axis label right, clear of the head
    row = [                                                # (scheme, glyph, colour, title, text)
        ("red", "terminal", "security", "Manual deploys", "SSH / console by\nhand; no audit trail"),
        ("orange", "script", "compute", "Scripts & cron", "Repeatable but brittle;\nstill needs stored keys"),
        ("yellow", "rolling", "gold", "Rolling update", "Old + new mixed; no\ntest listener"),
        ("green", "bluegreen", "teal", "Blue/green", "Full new copy beside\nold; instant switch back"),
        ("green", "canary", "storage", "Canary / linear", "10% first, alarms watch,\nauto rollback"),
    ]
    for i, (sc, k, c, t, d) in enumerate(row):            # Five approach boxes
        x = 9 + i * 136                                    # Box x
        b += box(x, 38, 118, 112, sc, sw=1.3 if i == 4 else 1)  # Shape
        b += icon(k, x + 59, 62, 30, c)                    # Icon
        b += text(x + 59, 95, t, 11, "bold")               # Title
        b += text(x + 59, 112, d, 9, color="#333")         # Description
        if i < 4:                                          # Arrow to next box
            b += arrow([(x + 118, 94), (x + 136, 94)])
    tools = [                                              # (scheme, glyph, colour, title, text)
        ("blue", "server", "devtools", "Self-hosted CI (Jenkins, GitLab)", "Flexible, but servers to patch\nand cloud keys stored in CI"),
        ("purple", "sparkle", "network", "Managed platforms", "Beanstalk, App Runner, ECS native:\nless control of network & pipeline"),
        ("green", "check", "storage", "Chosen for Onward", "GitHub Actions (OIDC) + CodePipeline\n+ CodeDeploy canary blue/green"),
    ]
    for i, (sc, k, c, t, d) in enumerate(tools):          # Tooling row
        x = 9 + i * 225                                    # Box x
        b += box(x, 178, 212, 76, sc, sw=2 if i == 2 else 1, dash=(i != 2))  # Shape (chosen is solid + bold)
        b += icon(k, x + 26, 216, 32, c)                   # Icon
        b += text(x + 50, 205, t, 10.5, "bold", "start")   # Title
        b += text(x + 50, 221, d, 9, anchor="start", color="#333")  # Description
    b += arrow([(625, 150), (625, 176)], color="#82b366", marker="arrg", label="adopted", at=(648, 166), width=1.6)  # Canary → chosen
    b += text(9, 172, "Where the release process runs", 9.5, "bold", "start", "#555")  # Row caption
    return svg(680, 262, b)


def fig_no_solution():
    """Figure 3: consequences of having no safe delivery process."""
    b = box(245, 128, 190, 74, "red", sw=2.2)              # Central problem
    b += icon("warning", 276, 165, 36, "security")         # Warning icon
    b += text(362, 160, "No safe delivery\nprocess", 12, "bold", "middle", "#7a2320")  # Problem text
    cons = [                                               # (x, y, glyph, colour, title, text)
        (8, 18, "clock", "integration", "Downtime on release", "Customers see errors while\nthey place orders"),
        (245, 18, "drift", "compute", "Inconsistent releases", "Steps differ per engineer;\nenvironments drift apart"),
        (482, 18, "unlock", "security", "Credential leakage", "Long-lived keys on laptops\nand in CI secrets"),
        (8, 240, "undo", "network", "No fast rollback", "Reverting means another\nmanual deploy under pressure"),
        (245, 240, "frown", "gold", "Release fear", "Changes get batched, so\neach release is riskier"),
        (482, 240, "cart", "people", "Peak-day risk", "The busiest days become\nthe riskiest days to ship"),
    ]
    for x, y, k, c, t, d in cons:                          # Consequence boxes
        b += box(x, y, 190, 70, "grey", fill="#ffffff", stroke=C[c], sw=1.4)  # Shape in icon colour
        b += icon(k, x + 27, y + 35, 32, c)                # Icon
        b += text(x + 50, y + 27, t, 10.5, "bold", "start")  # Title
        b += text(x + 50, y + 43, d, 9, anchor="start", color="#333")  # Description
    red = dict(color="#b85450", marker="arrr")             # Red connector style
    b += arrow([(290, 128), (290, 108), (103, 108), (103, 90)], **red)  # → top-left
    b += arrow([(340, 128), (340, 90)], **red)             # → top-centre
    b += arrow([(390, 128), (390, 108), (577, 108), (577, 90)], **red)  # → top-right
    b += arrow([(290, 202), (290, 222), (103, 222), (103, 240)], **red)  # → bottom-left
    b += arrow([(340, 202), (340, 240)], **red)            # → bottom-centre
    b += arrow([(390, 202), (390, 222), (577, 222), (577, 240)], **red)  # → bottom-right
    return svg(680, 318, b)


def fig_architecture():
    """Figure 4: target architecture with the numbered flow of a change."""
    b = group(8, 10, 220, 196, "GitHub", "#57606a", kind="repo", fill="#fafbfc", dash=True)  # GitHub group
    b += icon("user", 45, 60, 36, "people", "Developer", round_=True)  # Developer
    b += icon("repo", 118, 60, 36, "github", "App repo")   # App repo
    b += icon("actions", 190, 60, 36, "github", "Actions")  # GitHub Actions
    b += icon("repo", 118, 158, 36, "github", "Infra repo")  # Infra repo
    b += arrow([(64, 60), (99, 60)]) + badge(1, 81, 44)    # 1 merge
    b += arrow([(137, 60), (171, 60)])                     # Repo triggers workflow

    b += group(238, 10, 434, 522, "AWS Cloud · eu-west-1", "#232F3E", kind="cloud")  # AWS Cloud group
    row1 = [("ecr", 285, "compute", "Amazon ECR"), ("eventbridge", 365, "integration", "EventBridge"),
            ("pipeline", 445, "devtools", "CodePipeline"), ("codedeploy", 525, "devtools", "CodeDeploy"),
            ("cloudwatch", 615, "integration", "CloudWatch\nalarms")]  # Delivery services
    for k, x, c, lab in row1:                              # Draw row 1
        b += icon(k, x, 60, 36, c, lab)
    b += arrow([(209, 60), (266, 60)]) + badge(2, 238, 44)  # 2 push image
    b += arrow([(304, 60), (346, 60)]) + badge(3, 325, 44)  # 3 push event
    b += arrow([(384, 60), (426, 60)]) + badge(4, 405, 44)  # 4 start pipeline
    b += arrow([(464, 60), (506, 60)]) + badge(5, 485, 44)  # 5 deploy
    b += arrow([(596, 60), (544, 60)], dashed=True, color="#b85450", marker="arrr", label="rollback", at=(570, 54))  # Alarms → rollback

    row2 = [("cfn", 285, "integration", "CloudFormation\nGitSync"), ("iam", 365, "security", "IAM OIDC\nprovider"),
            ("scaling", 445, "compute", "Auto Scaling\n2–6 tasks")]  # Platform services
    for k, x, c, lab in row2:                              # Draw row 2
        b += icon(k, x, 158, 36, c, lab)
    b += arrow([(137, 158), (266, 158)], label="GitSync", at=(185, 152))  # Infra repo → stacks
    b += arrow([(190, 98), (190, 122), (365, 122), (365, 139)], dashed=True, label="OIDC → STS (1 h)", at=(300, 118))  # OIDC, starts below the label

    b += group(248, 222, 414, 302, "VPC 10.20.0.0/16 · no NAT gateway", "#8C4FFF", kind="vpc")  # VPC
    b += group(256, 246, 196, 270, "Availability Zone eu-west-1a", "#147EBA", dash=True, center=True)  # AZ a
    b += group(460, 246, 196, 270, "Availability Zone eu-west-1b", "#147EBA", dash=True, center=True)  # AZ b
    b += group(264, 266, 180, 54, "Public subnet", "#7AA116", fill="#F2F6E8")  # Public a
    b += group(468, 266, 180, 54, "Public subnet", "#7AA116", fill="#F2F6E8")  # Public b
    b += group(264, 360, 180, 148, "Private subnet · no 0.0.0.0/0", "#147EBA", fill="#E6F2F8")  # Private a
    b += group(468, 360, 180, 148, "Private subnet · no 0.0.0.0/0", "#147EBA", fill="#E6F2F8")  # Private b

    b += icon("alb", 456, 298, 36, "network")              # ALB spanning both public subnets
    b += text(478, 296, "Application Load Balancer", 8.5, "bold", "start")  # ALB label
    b += text(478, 307, "prod :80 · test :8080", 8.5, anchor="start", color="#333")  # Listener note

    b += icon("cart", 45, 298, 36, "people", "Customers", round_=True)  # Customers
    b += arrow([(64, 298), (437, 298)], label="HTTP", at=(150, 292))  # Internet → ALB

    for cx, tb, tg, ep in ((322, 300, 345, 410), (526, 504, 549, 614)):  # Tasks + endpoints per AZ
        b += icon("fargate", tb, 415, 30, "compute")       # Blue task set member
        b += icon("fargate", tg, 415, 30, "compute")       # Green task set member
        b += text(tb, 442, "blue", 8.5, "bold", color="#3b6fb6") + text(tg, 442, "green", 8.5, "bold", color="#3f8a3f")  # Set captions
        b += text(cx, 456, "Fargate tasks", 8.5, color="#333")  # Caption
        b += icon("endpoint", ep, 415, 30, "network", "Interface\nendpoints", lsize=8.5)  # Endpoints
        b += arrow([(tg + 16, 415), (ep - 16, 415)], label="443", at=((tg + ep) / 2, 410), lsize=8)  # Task → endpoint
    b += arrow([(450, 317), (450, 338), (322, 338), (322, 398)], label="TG blue ⇄ TG green", at=(386, 333), lsize=8.5)  # ALB → AZ a
    b += arrow([(462, 317), (462, 338), (526, 338), (526, 398)])  # ALB → AZ b
    b += arrow([(525, 98), (525, 212), (456, 212), (456, 279)]) + badge(6, 525, 196)  # 6 shift traffic, lands on the ALB
    b += icon("s3", 284, 490, 22, "storage")               # S3 gateway endpoint
    b += text(299, 494, "S3 gateway endpoint (free)", 8.5, anchor="start", color="#333")  # Caption
    b += text(476, 494, "ECR / Logs reached privately", 8.5, anchor="start", color="#333")  # Caption
    return svg(680, 540, b)


def fig_stakeholders():
    """Figure 5: stakeholder need → AWS services that answer it."""
    b = text(88, 18, "Stakeholder", 10, "bold", color="#555")  # Column header
    b += text(300, 18, "Need (from the client brief)", 10, "bold", color="#555")  # Column header
    b += text(551, 18, "Services that answer it", 10, "bold", color="#555")  # Column header
    rows = [                                               # (scheme, glyph, colour, name, role, need, services)
        ("blue", "cart", "people", "Customers", "Place orders 24/7",
         "Orders keep working during every\nrelease; a bad version reaches\nonly a few users, briefly.",
         [("alb", "network", "ALB"), ("codedeploy", "devtools", "Canary"), ("cloudwatch", "integration", "Alarms")]),
        ("yellow", "star", "gold", "CTO", "Delivery owner",
         "Merge is the only manual step.\nNo outage on release. Fast\nrollback. Readable for newcomers.",
         [("actions", "github", "Actions"), ("eventbridge", "integration", "EventBridge"), ("pipeline", "devtools", "Pipeline"),
          ("codedeploy", "devtools", "CodeDeploy"), ("cfn", "integration", "GitSync")]),
        ("red", "shield", "security", "Head of Security", "Risk & compliance",
         "No long-lived credentials. One\npublic entry point. The app has\nno path to the internet.",
         [("iam", "security", "OIDC"), ("alb", "network", "ALB only"), ("endpoint", "network", "Endpoints"), ("ecr", "compute", "ECR scan")]),
        ("green", "gear", "teal", "Head of Operations", "Runs the platform",
         "Survive a container or AZ failure.\nScale up and down without\nmanual action.",
         [("fargate", "compute", "Fargate"), ("scaling", "compute", "Scaling"), ("alb", "network", "Health"), ("cloudwatch", "integration", "Insights")]),
        ("purple", "money", "network", "Finance Lead", "Budget owner",
         "Idle environments should cost\nnothing. Understand the cost\nof private connectivity.",
         [("fargate", "compute", "Per-second"), ("cfn", "integration", "Teardown"), ("scaling", "compute", "Scale to 0"), ("s3", "storage", "Free S3 GW")]),
    ]
    for i, (sc, k, c, name, role, need, svcs) in enumerate(rows):  # One swimlane row per stakeholder
        y = 30 + i * 80                                    # Row top
        cy = y + 34                                        # Row centre
        b += box(8, y, 160, 68, sc, sw=1.3)                # Stakeholder card
        b += icon(k, 38, cy, 34, c, round_=True)           # Person icon
        b += text(62, cy - 3, name, 10.5, "bold", "start")  # Name
        b += text(62, cy + 12, role, 9, anchor="start", color="#444")  # Role
        b += arrow([(168, cy), (188, cy)])                 # → need
        b += box(188, y, 222, 68, "grey", fill="#ffffff", stroke=DRAWIO[sc][1])  # Need box
        b += f'<rect x="188" y="{y}" width="6" height="68" rx="2" fill="{DRAWIO[sc][1]}"/>'  # Colour bar
        b += ctext(0, cy, need, 9.5, anchor="start", x=202)  # Need text
        b += arrow([(410, cy), (430, cy)])                 # → services
        b += box(430, y, 242, 68, "grey", fill="#fbfbfb", stroke="#cfcfcf", dash=True)  # Services container
        for j, (sk, scol, slab) in enumerate(svcs):        # Service icons
            b += icon(sk, 456 + j * 47, cy - 8, 28, scol, slab, lsize=8)
    return svg(680, 432, b)


def fig_before_after():
    """Figure 6: release process today vs with the solution (draw.io swimlanes)."""
    lanes = [                                              # (y, header colour, scheme, title, steps)
        (8, "#b85450", "red", "Today", [
            ("unlock", "security", "Engineer gets\nAWS keys"), ("terminal", "gold", "Build on a\nlaptop"),
            ("terminal", "compute", "SSH / console\ndeploy"), ("clock", "integration", "Restart =\noutage window"),
            ("undo", "network", "Problem? Manual\nredeploy")]),
        (132, "#4d7c3a", "green", "With the solution", [
            ("repo", "github", "Merge PR (only\nmanual step)"), ("actions", "github", "Test + build,\nOIDC, no keys"),
            ("ecr", "compute", "Push to ECR,\nevent fires"), ("codedeploy", "devtools", "Canary 10% → 100%,\nzero downtime"),
            ("cloudwatch", "integration", "Alarm? Auto\nrollback")]),
    ]
    b = ""                                                 # Figure body
    for y, hc, sc, title, steps in lanes:                  # Each swimlane
        b += f'<rect x="8" y="{y}" width="664" height="112" fill="#fff" stroke="{hc}" stroke-width="1.3"/>'  # Lane frame
        b += f'<rect x="8" y="{y}" width="30" height="112" fill="{DRAWIO[sc][0]}" stroke="{hc}" stroke-width="1.3"/>'  # Lane header
        b += (f'<text transform="translate(27,{y+56}) rotate(-90)" font-size="10.5" font-weight="bold" '
              f'text-anchor="middle" fill="{hc}">{esc(title)}</text>')  # Vertical lane title
        for i, (k, c, lab) in enumerate(steps):            # Steps
            x = 50 + i * 125                               # Step x
            b += box(x, y + 18, 112, 76, sc, fill="#ffffff", stroke=hc)  # Step box
            b += icon(k, x + 56, y + 40, 28, c)            # Step icon
            b += text(x + 56, y + 70, lab, 9, color="#222")  # Step text
            if i < 4:                                      # Connector
                b += arrow([(x + 112, y + 56), (x + 125, y + 56)], color=hc, marker="arrr" if sc == "red" else "arrg")
    return svg(680, 254, b)


# ============================================================================ PAGES

def canvas(fig, n, title, file_tab):
    """A figure framed like a draw.io editor canvas (tab + grid)."""
    return (f'<div class="canvas"><div class="tab"><span class="dot r"></span><span class="dot y"></span>'
            f'<span class="dot g"></span><b>{esc(file_tab)}</b><span class="pg">Page-{n}</span></div>'
            f'<div class="grid">{fig}</div><div class="cap">Figure {n} · {esc(title)}</div></div>')


def page(n, total, part, body):
    """One A4 page with header band and footer."""
    return (f'<section class="page"><header><span class="brand">{icon_html("cart", "compute", 18)} '
            f'Onward Logistics · Discovery Report</span><span class="part">{esc(part)}</span></header>'
            f'{body}<footer><span>{esc(AUTHOR)} · {esc(LAB)}</span><span>{n} / {total}</span></footer></section>')


def h(num, title, color):
    """Section heading with a coloured number chip."""
    return f'<h2><span class="chip" style="background:{color}">{esc(num)}</span>{esc(title)}</h2>'


def card(kind, color, title, body):
    """Small icon card for summary grids."""
    return (f'<div class="card" style="border-top-color:{C[color]}">{icon_html(kind, color, 28)}'
            f'<div><b>{esc(title)}</b><p>{body}</p></div></div>')


def build_pages():
    """All report pages in order."""
    total = 7                                              # Page count shown in footers
    pages = []                                             # Collected pages

    legend = "".join(                                      # Icon colour legend
        f'<span class="lg"><i style="background:{C[k]}"></i>{esc(v)}</span>'
        for k, v in [("compute", "Compute & containers"), ("network", "Networking"), ("security", "Security & identity"),
                     ("devtools", "Developer tools"), ("integration", "Integration & management"), ("storage", "Storage"),
                     ("github", "GitHub")]
    )
    pages.append(f"""
      <div class="cover">
        <div class="eyebrow">AWS Developer Lab · Discovery Report</div>
        <h1>Safe Order System Delivery<br>for Onward Logistics</h1>
        <div class="sub">{esc(LAB)}</div>
        <div class="meta">
          <span>{icon_html("user", "people", 18, True)} <b>Prepared by</b> {esc(AUTHOR)}</span>
          <span>{icon_html("clock", "integration", 18, True)} <b>Date</b> {DATE}</span>
          <span>{icon_html("cloud", "devtools", 18, True)} <b>Region</b> eu-west-1</span>
        </div>
      </div>
      {canvas(fig_flow(), 1, "From merge to customers: the eight automated steps of one release", "onward-delivery.drawio")}
      <div class="grid4">
        {card("target", "devtools", "Goal", "Every approved change reaches customers automatically, safely, with zero downtime and easy rollback.")}
        {card("rocket", "compute", "Approach", "ECS Fargate behind one ALB, released by CodeDeploy blue/green with canary traffic and alarm rollback.")}
        {card("shield", "security", "Security", "No stored keys (GitHub OIDC), one public entry point, no internet path for the app.")}
        {card("money", "storage", "Cost", "About $94/month while running; teardown makes an idle environment cost nothing.")}
      </div>
      <div class="toc"><b>Contents</b>
        <ol><li>Part A.1 · How teams deliver changes today</li><li>Part A.2 · What happens without a solution</li>
        <li>Part B.1 · Chosen approach and architecture</li><li>Part B.2 · Services, and why each one</li>
        <li>Part B.3 · Who benefits</li><li>Sources</li></ol></div>
      <div class="legend"><b>Icon colours</b>{legend}</div>""")

    pages.append(f"""
      {h("A.1", "How teams deliver changes: common solutions", C["devtools"])}
      <p class="lead">Release practices range from hands-on manual deploys to fully automated, progressive
      releases. Moving right in Figure 2 lowers the chance that a bad change reaches customers, and the time it takes to undo one.</p>
      {canvas(fig_approaches(), 2, "Delivery approaches ordered by release risk, and where the release process runs", "approaches.drawio")}
      <table class="dt">
        <tr><th>Approach</th><th>How it works</th><th>Strength</th><th>Weakness for Onward</th></tr>
        <tr><td>{icon_html("terminal", "security", 18)} Manual deploys</td><td>Engineer copies files and restarts the app</td><td>No tooling needed</td><td>Slow, error-prone, standing credentials, no audit trail</td></tr>
        <tr><td>{icon_html("script", "compute", 18)} Scripts / cron</td><td>Shell scripts run the same steps</td><td>Repeatable</td><td>Brittle, still needs keys, no traffic control</td></tr>
        <tr><td>{icon_html("rolling", "gold", 18)} Rolling update</td><td>Tasks replaced a few at a time</td><td>Built into ECS, no extra cost</td><td>Old and new serve together; rollback is another rollout</td></tr>
        <tr><td>{icon_html("bluegreen", "teal", 18)} Blue/green</td><td>Full new copy starts beside the old one; traffic switches</td><td>Instant switch back; test before going live</td><td>Briefly runs two copies</td></tr>
        <tr><td>{icon_html("canary", "storage", 18)} Canary / linear</td><td>A small share of traffic goes to the new version first</td><td>Limits how many users a bad release reaches</td><td>Needs health signals (alarms)</td></tr>
        <tr><td>{icon_html("server", "devtools", 18)} Jenkins / GitLab CI</td><td>Self-hosted or SaaS CI/CD servers</td><td>Very flexible</td><td>Servers to patch; often long-lived cloud keys</td></tr>
        <tr><td>{icon_html("sparkle", "network", 18)} Beanstalk, App Runner, ECS native</td><td>Managed release features</td><td>Less to build</td><td>Less control over the private network and pipeline the brief requires</td></tr>
      </table>
      <p class="src">Sources: [1] Well-Architected OPS06 · [2] Blue/Green Deployments on AWS · [3] ECS blue/green with CodeDeploy · [4] CodeDeploy deployment configurations.</p>""")

    pages.append(f"""
      {h("A.2", "What happens without a solution", C["security"])}
      <p class="lead">Without an automated, reversible release process, each change is a risk to the order system. Figure 3 shows
      the six consequences, and each one costs Onward either orders, security, or engineering time.</p>
      {canvas(fig_no_solution(), 3, "Consequences of shipping without a safe delivery process", "no-solution.drawio")}
      <div class="note"><div class="fold"></div><b>Business impact</b>
        <ul>
          <li>{icon_html("cart", "people", 16)} <b>Lost orders.</b> Every minute of downtime during a release is revenue that does not come back.</li>
          <li>{icon_html("unlock", "security", 16)} <b>Breach exposure.</b> Long-lived access keys are a leading cause of cloud security incidents [8].</li>
          <li>{icon_html("clock", "integration", 16)} <b>Slow change.</b> Fear of releases leads to large, infrequent batches, which make every release riskier [1].</li>
          <li>{icon_html("drift", "compute", 16)} <b>Hard to rebuild.</b> Hand-made environments drift, so problems cannot be reproduced or recovered from quickly.</li>
        </ul></div>
      <p class="src">Sources: [1] Well-Architected OPS06 · [5] GitHub OIDC for AWS · [8] Well-Architected SEC02 temporary credentials.</p>""")

    pages.append(f"""
      {h("B.1", "Chosen approach and architecture", C["compute"])}
      <p class="lead"><b>ECS on Fargate in private subnets behind a single ALB.</b> GitHub Actions (OIDC) pushes the image to ECR. EventBridge
      starts CodePipeline, and CodeDeploy releases it blue/green with canary traffic and alarm-based automatic rollback. All
      infrastructure is CloudFormation deployed by GitSync, and AWS services are reached through VPC endpoints, not a NAT gateway.</p>
      {canvas(fig_architecture(), 4, "Target architecture and the numbered flow of one change", "onward-architecture.drawio")}
      <ol class="steps">
        <li><b>Merge</b> to <code>main</code> in the app repo. This is the only manual step.</li>
        <li><b>GitHub Actions</b> tests, assumes an IAM role through OIDC (1-hour credentials, no stored keys), and pushes <code>:&lt;sha&gt;</code> and <code>:latest</code> to <b>ECR</b>.</li>
        <li>ECR emits an <b>Image Action PUSH</b> event.</li>
        <li>An <b>EventBridge</b> rule starts <b>CodePipeline</b>. There is no polling.</li>
        <li>The pipeline registers a new task definition and calls <b>CodeDeploy</b>.</li>
        <li>CodeDeploy starts the green tasks in both AZs, shifts <b>10% of traffic for 5 minutes, then 100%</b>, and <b>rolls back automatically</b> if an alarm fires.</li>
      </ol>""")

    svc = [                                                # (glyph, colour, service, why, stakeholder)
        ("alb", "network", "Application Load Balancer", "Single public entry point, health checks, prod + test listeners for blue/green", "Security, CTO"),
        ("fargate", "compute", "Amazon ECS on Fargate", "No servers to patch; tasks spread over two AZs", "Operations"),
        ("scaling", "compute", "Application Auto Scaling", "CPU/memory target tracking, 2–6 tasks; scale to zero when idle", "Operations, Finance"),
        ("ecr", "compute", "Amazon ECR", "Private registry, scan on push, immutable SHA tags for rollback", "Security, CTO"),
        ("endpoint", "network", "VPC endpoints", "ECR, Logs and S3 reached without any internet route", "Security"),
        ("iam", "security", "IAM + GitHub OIDC", "Temporary STS credentials; trust limited to one repo and branch", "Security"),
        ("eventbridge", "integration", "Amazon EventBridge", "Image push event starts the release, with no polling", "CTO"),
        ("pipeline", "devtools", "CodePipeline + CodeDeploy", "Managed blue/green, canary shift, automatic rollback", "CTO, Customers"),
        ("cloudwatch", "integration", "Amazon CloudWatch", "5XX and unhealthy-host alarms stop bad releases", "CTO, Operations"),
        ("cfn", "integration", "CloudFormation GitSync", "Reviewed, repeatable infrastructure; rebuild or tear down from Git", "CTO, Finance"),
    ]
    rows = "".join(f'<tr><td>{icon_html(k, c, 18)} <b>{esc(s)}</b></td><td>{esc(w)}</td><td>{esc(p)}</td></tr>' for k, c, s, w, p in svc)  # Table rows
    pages.append(f"""
      {h("B.2", "Services, and why each one", C["integration"])}
      <p class="lead">Each service in the solution is there because a stakeholder asked for what it provides. Figure 5 traces every
      stakeholder need to the services that meet it.</p>
      {canvas(fig_stakeholders(), 5, "Stakeholder needs mapped to AWS services", "stakeholder-map.drawio")}
      <table class="dt"><tr><th>Service</th><th>Why it is used</th><th>Serves</th></tr>{rows}</table>""")

    pages.append(f"""
      {h("B.3", "Who benefits", C["storage"])}
      <p class="lead">The same release, before and after. The manual chain of risky steps becomes an automated chain where
      the only human action is approving a merge.</p>
      {canvas(fig_before_after(), 6, "Release process today vs with the solution", "before-after.drawio")}
      <div class="grid3">
        {card("cart", "people", "Customers", "No outage during releases. A bad release reaches at most 10% of traffic, for minutes, before rollback.")}
        {card("star", "gold", "CTO", "Merging is the whole release process. Releases become frequent, small, and routine.")}
        {card("shield", "security", "Head of Security", "No keys to leak, one public door, and an application that cannot reach the internet.")}
        {card("gear", "teal", "Head of Operations", "Self-healing tasks across two AZs, automatic scaling, and alarms watching every release.")}
        {card("money", "network", "Finance Lead", "Per-second Fargate billing, scale-to-zero or teardown when idle, and a clear endpoint cost.")}
        {card("book", "devtools", "Engineers", "Two small, documented repos, and the same environment rebuilt from code every time.")}
      </div>
      <div class="note green"><div class="fold"></div><b>Cost in one line</b>
        <p>About $94/month while running (eu-west-1): ~$48 interface endpoints, ~$24 ALB, ~$18 Fargate, plus small amounts for logs and alarms.
        Endpoints cost about $13 more than one NAT gateway, but NAT would give the app an internet path, which Security rules out.
        Teardown brings the idle cost to zero.</p></div>""")

    srcs = [                                               # (title, url)
        ("AWS Well-Architected Framework, Operational Excellence: OPS06 Mitigate deployment risks", "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/"),
        ("AWS Whitepaper: Blue/Green Deployments on AWS", "https://docs.aws.amazon.com/whitepapers/latest/blue-green-deployments/"),
        ("Amazon ECS Developer Guide: Blue/green deployment with CodeDeploy", "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-type-bluegreen.html"),
        ("AWS CodeDeploy User Guide: Deployment configurations on an ECS compute platform", "https://docs.aws.amazon.com/codedeploy/latest/userguide/deployment-configurations.html"),
        ("GitHub Docs: Configuring OpenID Connect in Amazon Web Services", "https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services"),
        ("Amazon ECR User Guide: Interface VPC endpoints (AWS PrivateLink)", "https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html"),
        ("AWS CloudFormation User Guide: Git sync", "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/git-sync.html"),
        ("AWS Well-Architected Framework, Security: SEC02 Use temporary credentials", "https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/"),
        ("AWS Pricing Calculator (prices used in the cost estimate)", "https://calculator.aws/"),
    ]
    items = "".join(f'<li>{icon_html("link", "devtools", 16)} <b>[{i}]</b> {esc(t)}<br><a href="{u}">{esc(u)}</a></li>'
                    for i, (t, u) in enumerate(srcs, 1))   # Source list
    pages.append(f"""
      {h("S", "Sources", C["devtools"])}
      <ul class="sources">{items}</ul>
      <div class="note"><div class="fold"></div><b>Assumptions</b>
        <ul>
          <li>Stakeholder needs are summarised from the client brief. They are not verbatim quotes.</li>
          <li>Prices are approximate eu-west-1 on-demand list prices. Confirm them in the AWS Pricing Calculator.</li>
          <li>Naming and tags follow the pattern <code>onward-orders-lab-*</code> with Project, Environment, Owner, CostCenter, ManagedBy and Repository tags.</li>
        </ul></div>
      <p class="lead">Full implementation: <b>onward-orders-infra</b> (CloudFormation + GitSync) and <b>onward-orders-app</b> (code, Dockerfile,
      workflow, appspec, task definition). Detailed costs are in <code>docs/cost-analysis.md</code>.</p>""")

    return "".join(page(i + 1, total, part, body) for i, (part, body) in enumerate(zip(
        ["Overview", "Part A · What I found", "Part A · What I found", "Part B · Business value",
         "Part B · Business value", "Part B · Business value", "References"], pages)))  # Wrap pages


CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; font-family: Helvetica, Arial, sans-serif; color: #1d1d1d; font-size: 10.5pt; background: #e9ecef; }
.page { width: 210mm; height: 297mm; padding: 15mm 14mm 14mm; position: relative; background: #fff; overflow: hidden;
        page-break-after: always; margin: 0 auto; }
header { position: absolute; top: 0; left: 0; right: 0; height: 10mm; display: flex; justify-content: space-between;
         align-items: center; padding: 0 14mm; background: #232F3E; color: #fff; font-size: 8.5pt; }
header .brand { display: flex; align-items: center; gap: 6px; font-weight: bold; }
header .part { color: #ffb366; }
footer { position: absolute; bottom: 6mm; left: 14mm; right: 14mm; display: flex; justify-content: space-between;
         font-size: 8pt; color: #777; border-top: 1px solid #ddd; padding-top: 2mm; }
h1 { font-size: 27pt; margin: 4mm 0 2mm; line-height: 1.12; color: #232F3E; }
h2 { font-size: 15pt; margin: 4mm 0 2mm; display: flex; align-items: center; gap: 8px; color: #232F3E; }
.chip { color: #fff; font-size: 10pt; padding: 3px 8px; border-radius: 4px; }
.lead { margin: 1mm 0 3mm; line-height: 1.45; }
.cover { margin-top: 2mm; padding: 6mm 7mm; border-radius: 6px; color: #fff;
         background: linear-gradient(135deg, #232F3E 0%, #2e4a6b 60%, #3B48CC 100%); }
.cover h1 { color: #fff; }
.eyebrow { color: #ffb366; font-weight: bold; letter-spacing: .5px; font-size: 9pt; text-transform: uppercase; }
.sub { font-size: 12pt; color: #dfe6ee; }
.meta { display: flex; gap: 16px; margin-top: 4mm; font-size: 9pt; flex-wrap: wrap; }
.meta span { display: flex; align-items: center; gap: 5px; background: rgba(255,255,255,.12); padding: 3px 8px; border-radius: 12px; }
.canvas { border: 1px solid #c7c7c7; border-radius: 6px; margin: 3mm 0; overflow: hidden; background: #fff; }
.tab { display: flex; align-items: center; gap: 5px; background: #f1f3f4; border-bottom: 1px solid #d6d6d6;
       padding: 3px 8px; font-size: 7.5pt; color: #444; }
.tab b { margin-left: 6px; font-weight: normal; }
.tab .pg { margin-left: auto; background: #fff; border: 1px solid #ccc; border-bottom: none; padding: 0 8px; border-radius: 3px 3px 0 0; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot.r { background: #ff5f57; } .dot.y { background: #febc2e; } .dot.g { background: #28c840; }
.grid { padding: 3mm; background-color: #fff;
        background-image: linear-gradient(#e6e6e6 1px, transparent 1px), linear-gradient(90deg, #e6e6e6 1px, transparent 1px),
                          linear-gradient(#f4f4f4 1px, transparent 1px), linear-gradient(90deg, #f4f4f4 1px, transparent 1px);
        background-size: 40px 40px, 40px 40px, 10px 10px, 10px 10px; }
.fig { width: 100%; height: auto; display: block; }
.cap { font-size: 8pt; color: #555; padding: 2px 8px 4px; border-top: 1px solid #eee; font-style: italic; }
.ico { vertical-align: middle; flex: none; }
.grid4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 3mm; margin: 3mm 0; }
.grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 3mm; margin: 3mm 0; }
.card { display: flex; gap: 8px; border: 1px solid #ddd; border-top: 4px solid; border-radius: 6px; padding: 7px 8px; background: #fff; }
.card b { font-size: 10pt; } .card p { margin: 2px 0 0; font-size: 8.5pt; line-height: 1.35; color: #333; }
.toc { float: left; width: 52%; font-size: 9pt; } .toc ol { margin: 1mm 0 0; padding-left: 18px; line-height: 1.55; }
.legend { float: right; width: 45%; font-size: 8.5pt; display: flex; flex-wrap: wrap; gap: 4px 10px; align-content: flex-start; }
.legend b { width: 100%; font-size: 9pt; }
.lg { display: inline-flex; align-items: center; gap: 4px; } .lg i { width: 11px; height: 11px; border-radius: 3px; display: inline-block; }
.dt { width: 100%; border-collapse: collapse; font-size: 8.6pt; margin: 2mm 0; }
.dt th { background: #dae8fc; border: 1px solid #6c8ebf; text-align: left; padding: 4px 6px; }
.dt td { border: 1px solid #c9d6ea; padding: 3px 6px; vertical-align: middle; }
.dt tr:nth-child(odd) td { background: #f7faff; }
.src { font-size: 8pt; color: #666; font-style: italic; }
.note { position: relative; background: #fff2cc; border: 1px solid #d6b656; padding: 4mm 5mm; margin: 3mm 0; font-size: 9.5pt;
        clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%); }
.note .fold { position: absolute; right: 0; top: 0; width: 18px; height: 18px; background: linear-gradient(225deg, transparent 50%, #e8d38e 50%); }
.note ul { margin: 2mm 0 0; padding-left: 0; list-style: none; line-height: 1.6; }
.note p { margin: 1mm 0 0; line-height: 1.45; }
.note.green { background: #d5e8d4; border-color: #82b366; }
.note.green .fold { background: linear-gradient(225deg, transparent 50%, #a9cfa5 50%); }
.steps { margin: 2mm 0; padding-left: 0; list-style: none; counter-reset: s; font-size: 9.3pt; line-height: 1.4; }
.steps li { counter-increment: s; margin: 0 0 1.6mm; padding-left: 26px; position: relative; }
.steps li::before { content: counter(s); position: absolute; left: 0; top: 0; width: 18px; height: 18px; border-radius: 50%;
                    background: #232F3E; color: #fff; font-size: 9pt; font-weight: bold; text-align: center; line-height: 18px; }
code { background: #eef2f5; padding: 0 4px; border-radius: 3px; font-size: 8.5pt; }
.sources { list-style: none; padding: 0; font-size: 9.5pt; line-height: 1.45; }
.sources li { margin-bottom: 3mm; } .sources a { color: #3B48CC; font-size: 8.5pt; word-break: break-all; }
@media screen { .page { margin: 8mm auto; box-shadow: 0 2px 10px #0003; } }
"""


def main():
    """Write the HTML, then print it to PDF with headless Chrome/Edge."""
    doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Discovery Report · Onward Logistics</title>'
           f'<style>{CSS}</style></head><body>{build_pages()}</body></html>')  # Full document
    OUT_HTML.write_text(doc, encoding="utf-8")             # Save HTML
    exe = next((p for p in CHROME if pathlib.Path(p).exists()), None)  # Find a browser
    if not exe:                                            # None installed
        sys.exit("Chrome or Edge not found; open the HTML and print to PDF manually.")
    subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={OUT_PDF}", OUT_HTML.as_uri()], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # Print to PDF
    print(f"Wrote {OUT_PDF}")                              # Report location


if __name__ == "__main__":                                 # Script entry point
    main()
