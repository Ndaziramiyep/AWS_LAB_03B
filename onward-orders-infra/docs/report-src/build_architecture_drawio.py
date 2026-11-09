"""Build docs/architecture.drawio (draw.io AWS shapes) and export it to SVG + PNG.

Run from onward-orders-infra:  python docs/report-src/build_architecture_drawio.py
The export uses draw.io's own viewer (viewer.diagrams.net) in headless Chrome, so internet is needed.
"""
import html                                                 # Escape XML attributes
import json                                                 # Embed the XML in the viewer page
import re                                                   # Pull the <svg> out of the rendered page
import subprocess                                           # Run Chrome
from pathlib import Path                                    # File paths

DOCS = Path(__file__).resolve().parents[1]                  # onward-orders-infra/docs
OUT_DRAWIO = DOCS / "architecture.drawio"                   # Editable source
OUT_SVG = DOCS / "architecture.svg"                         # Vector export
OUT_PNG = DOCS / "architecture.png"                         # Picture export
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"  # Headless browser
W, H = 1700, 1080                                           # Canvas size

cells = []                                                  # mxCell XML strings
_n = [1]                                                    # ID counter


def nid():
    """Return a new unique cell ID."""
    _n[0] += 1                                              # Next number
    return f"c{_n[0]}"                                      # ID text


def vertex(label, x, y, w, h, style):
    """Add a shape and return its ID."""
    i = nid()                                               # New ID
    cells.append(f'<mxCell id="{i}" value="{html.escape(label)}" style="{style}" vertex="1" parent="1">'
                 f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')  # Shape XML
    return i                                                # For edges


def edge(src, dst, label="", style="", pts=(), exit_=None, entry=None):
    """Add an orthogonal connector between two shapes (arcs where lines cross)."""
    s = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;strokeWidth=1.5;"
         "fontSize=11;labelBackgroundColor=#FFFFFF;jumpStyle=arc;jumpSize=10;" + style)  # draw.io connector look
    if exit_:                                               # Fixed exit point
        s += f"exitX={exit_[0]};exitY={exit_[1]};exitDx=0;exitDy=0;"
    if entry:                                               # Fixed entry point
        s += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
    p = "".join(f'<mxPoint x="{a}" y="{b}"/>' for a, b in pts)  # Waypoints
    arr = f'<Array as="points">{p}</Array>' if pts else ""  # Only if any
    cells.append(f'<mxCell id="{nid()}" value="{html.escape(label)}" style="{s}" edge="1" parent="1" '
                 f'source="{src}" target="{dst}"><mxGeometry relative="1" as="geometry">{arr}</mxGeometry></mxCell>')


# ---- Styles (draw.io AWS 2026 / aws4 library) ----
LBL = "verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=12;fontColor=#232F3E;"  # Label under icon
RIGHT = "labelPosition=right;verticalLabelPosition=middle;align=left;verticalAlign=middle;spacingLeft=4;"  # Label beside icon
TOP = "verticalLabelPosition=top;verticalAlign=bottom;"     # Label above icon


def svc(res, color):
    """AWS service icon (coloured square tile)."""
    return (f"sketch=0;outlineConnect=0;gradientColor=none;strokeColor=#ffffff;fillColor={color};dashed=0;"
            f"aspect=fixed;pointerEvents=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{res};" + LBL)


def res(shape, color):
    """AWS resource icon (glyph without tile)."""
    return (f"sketch=0;outlineConnect=0;gradientColor=none;strokeColor=none;fillColor={color};dashed=0;"
            f"aspect=fixed;pointerEvents=1;shape=mxgraph.aws4.{shape};" + LBL)


def grp(icon, stroke, fill="none", font=None, dashed=0):
    """AWS group frame (cloud, region, VPC, subnet)."""
    return (f"points=[];outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;fontStyle=1;"
            f"container=0;pointerEvents=0;collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;"
            f"grIcon=mxgraph.aws4.{icon};strokeColor={stroke};fillColor={fill};verticalAlign=top;align=left;"
            f"spacingLeft=30;fontColor={font or stroke};dashed={dashed};")


def frame(stroke, fill="none", dashed=1, font=None, align="center"):
    """Plain dashed frame (AZ, security group, GitHub)."""
    return (f"rounded=0;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};dashed={dashed};"
            f"verticalAlign=top;align={align};spacingLeft=8;fontStyle=1;fontSize=12;fontColor={font or stroke};")


def box(fill, stroke, bold=0):
    """draw.io default rounded rectangle."""
    return (f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontSize=11;"
            f"fontStyle={bold};arcSize=12;")


def badge(n, x, y):
    """Numbered step marker."""
    vertex(str(n), x, y, 26, 26, "ellipse;whiteSpace=wrap;html=1;aspect=fixed;fillColor=#232F3E;strokeColor=#FFFFFF;"
           "strokeWidth=2;fontColor=#FFFFFF;fontStyle=1;fontSize=13;")


def note(text, x, y, w, h):
    """Yellow draw.io note."""
    vertex(text, x, y, w, h, "shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;size=14;fillColor=#fff2cc;"
           "strokeColor=#d6b656;fontSize=11;align=left;spacingLeft=8;verticalAlign=top;spacingTop=4;")


# Colours from the AWS architecture icon set
COMPUTE, NET, SEC, DEV, MGMT, INTEG, STORE = "#ED7100", "#8C4FFF", "#DD344C", "#C925D1", "#E7157B", "#E7157B", "#7AA116"

# ---- Title ----
vertex("<b style='font-size:20px'>Onward Orders – target architecture (eu-west-1)</b><br>"
       "<span style='font-size:12px;color:#555'>GitHub → ECR → EventBridge → CodePipeline → CodeDeploy blue/green "
       "on ECS Fargate · private tasks · no NAT gateway</span>",
       20, 10, 900, 50, "text;html=1;align=left;verticalAlign=middle;whiteSpace=wrap;")

# ---- Outside AWS: people and GitHub ----
dev = vertex("Developer", 85, 100, 50, 50, res("user", "#232F3E") + RIGHT)  # Developer
vertex("GitHub", 20, 215, 200, 530, frame("#57606a", "#f6f8fa", 1, "#24292f", "left"))  # GitHub frame
gh_icon = "dashed=0;outlineConnect=0;html=1;shape=mxgraph.weblogos.github;" + LBL  # GitHub logo
app = vertex("onward-orders-app<br>(Flask code, appspec,<br>taskdef)", 90, 255, 50, 50, gh_icon)  # App repo
act = vertex("GitHub Actions<br>test · build · push", 90, 410, 50, 50, svc("codebuild", "#2088FF"))  # Actions
infra = vertex("onward-orders-infra<br>(CloudFormation)", 90, 590, 50, 50, gh_icon)  # Infra repo
cust = vertex("Customers", 85, 930, 50, 50, res("users", "#232F3E"))  # Customers

# ---- AWS Cloud / Region ----
vertex("AWS Cloud", 260, 80, 1420, 990, grp("group_aws_cloud_alt", "#232F3E"))  # Cloud
vertex("Region eu-west-1 (Ireland)", 280, 115, 1385, 940, grp("group_region", "#00A4A6", dashed=1, font="#147EBA"))  # Region

# Row of regional services (top)
Y = 165                                                     # Icon row y
cfn = vertex("AWS CloudFormation<br>Git sync (6 stacks)", 330, Y, 60, 60, svc("cloudformation", MGMT))
sts = vertex("IAM OIDC provider<br>+ AWS STS (1 h creds)", 530, Y, 60, 60, svc("identity_and_access_management", SEC))
ecr = vertex("Amazon ECR<br>immutable :sha", 730, Y, 60, 60, svc("ecr", COMPUTE))
evb = vertex("Amazon EventBridge<br>ECR PUSH rule", 930, Y, 60, 60, svc("eventbridge", INTEG))
cpl = vertex("AWS CodePipeline V2<br>(queued)", 1130, Y, 60, 60, svc("codepipeline", DEV))
cdp = vertex("AWS CodeDeploy<br>canary 10% · 5 min", 1330, Y, 60, 60, svc("codedeploy", DEV))
cwa = vertex("Amazon CloudWatch<br>5XX + unhealthy alarms", 1530, Y, 60, 60, svc("cloudwatch_2", MGMT))

# ---- VPC ----
vertex("VPC 10.20.0.0/16 · no NAT gateway", 300, 300, 1345, 740, grp("group_vpc2", NET, font="#AAB7B8"))
igw = vertex("Internet<br>gateway", 276, 425, 48, 48, res("internet_gateway", NET))  # On the VPC edge
s3 = vertex("S3 gateway<br>endpoint (free)", 1621, 830, 48, 48, res("endpoints", NET))  # On the VPC edge

AZ = [(330, "Availability Zone eu-west-1a", "10.20.0.0/24", "10.20.10.0/24", True),
      (1120, "Availability Zone eu-west-1b", "10.20.1.0/24", "10.20.11.0/24", False)]  # AZ x, name, CIDRs, left AZ?
tasks, eps = [], []                                         # Collected IDs per AZ
for x, name, pub, priv, left in AZ:                         # Draw each AZ (tasks sit next to the centre column)
    vertex(name, x, 340, 495, 680, frame("#147EBA"))         # AZ frame
    vertex(f"Public subnet {pub}", x + 15, 375, 465, 165, grp("group_security_group", "#7AA116", "#F2F6E8", "#248814"))
    vertex("ALB node", x + 215, 470, 48, 48, res("application_load_balancer", NET))  # ALB ENI in this AZ
    vertex(f"Private subnet {priv} · no 0.0.0.0/0 route", x + 15, 560, 465, 445,
           grp("group_security_group", "#00A4A6", "#E6F6F7", "#147EBA"))
    tsg, esg = (x + 230, x + 35) if left else (x + 35, x + 300)  # Task SG near the centre, endpoint SG outside
    vertex("task-sg (8080 from alb-sg)", tsg, 610, 230, 250, frame("#DD3522", font="#DD3522"))  # Task SG
    vertex("endpoint-sg<br>(443 from task-sg)", esg, 610, 160, 250, frame("#DD3522", font="#DD3522"))  # Endpoint SG
    bx, gx = (tsg + 40, tsg + 150) if left else (tsg + 150, tsg + 40)  # Green always closest to the centre
    tb = vertex("Fargate task<br><b>blue</b> (live)", bx, 670, 48, 48, res("fargate", COMPUTE))
    tg = vertex("Fargate task<br><b>green</b> (new)", gx, 670, 48, 48, res("fargate", COMPUTE))
    ep = vertex("Interface endpoints<br>ecr.api · ecr.dkr · logs", esg + 56, 690, 48, 48, res("endpoints", NET))
    edge(tb, ep, "443", "strokeColor=#147EBA;fontColor=#147EBA;")  # Task → endpoints
    tasks.append((tb, tg, bx, gx)); eps.append(ep)

# Centre column between the AZs: ALB, target groups, ECS, scaling
alb = vertex("<b>Application Load Balancer</b><br>alb-sg · prod :80 · test :8080", 865, 420, 60, 60,
             svc("elastic_load_balancing", NET) + TOP)
tgb = vertex("Target group <b>BLUE</b><br>/health · ip targets", 835, 575, 120, 44, box("#dae8fc", "#6c8ebf"))
tgg = vertex("Target group <b>GREEN</b><br>/health · ip targets", 835, 645, 120, 44, box("#d5e8d4", "#82b366"))
ecs = vertex("Amazon ECS service<br>CODE_DEPLOY<br>controller", 850, 760, 60, 60, svc("ecs", COMPUTE) + RIGHT)
asg = vertex("Application<br>Auto Scaling<br>2–6 tasks<br>CPU 55% · mem 75%", 850, 900, 60, 60,
             svc("application_auto_scaling", MGMT) + RIGHT)

# ---- Connectors and numbered flow ----
edge(dev, app, "merge to main", "strokeColor=#232F3E;"); badge(1, 142, 172)
edge(app, act, "", "strokeColor=#57606a;")
edge(act, ecr, "push image :sha + :latest", "strokeColor=#ED7100;fontColor=#ED7100;",
     pts=[(228, 420), (228, 268), (700, 268), (700, 210)], exit_=(1, 0.2), entry=(0, 0.75)); badge(2, 655, 255)
edge(act, sts, "OIDC → AssumeRoleWithWebIdentity", "dashed=1;strokeColor=#DD344C;fontColor=#DD344C;",
     pts=[(238, 440), (238, 288), (640, 288), (640, 210)], exit_=(1, 0.6), entry=(1, 0.75))
edge(ecr, evb, "PUSH :latest", "strokeColor=#E7157B;"); badge(3, 847, 165)
edge(evb, cpl, "start", "strokeColor=#E7157B;"); badge(4, 1047, 165)
edge(cpl, cdp, "deploy", "strokeColor=#C925D1;"); badge(5, 1247, 165)
edge(cwa, cdp, "rollback", "dashed=1;strokeColor=#B85450;fontColor=#B85450;")
edge(app, cpl, "appspec.yaml + taskdef.json via CodeConnections", "dashed=1;strokeColor=#57606a;fontColor=#57606a;",
     pts=[(200, 270), (200, 148), (1160, 148)], exit_=(1, 0.3), entry=(0.5, 0))
edge(infra, cfn, "git push → stack update", "dashed=1;strokeColor=#E7157B;fontColor=#E7157B;",
     pts=[(248, 615), (248, 195)], exit_=(1, 0.5), entry=(0, 0.5))
edge(cdp, ecs, "new green task set, shift traffic", "strokeColor=#C925D1;fontColor=#C925D1;",
     pts=[(1290, 216), (1290, 312), (1050, 312), (1050, 735), (880, 735)], exit_=(0, 0.85), entry=(0.5, 0)); badge(6, 1037, 380)
edge(cust, igw, "HTTP", "strokeColor=#232F3E;", pts=[(268, 955), (268, 449)], exit_=(1, 0.5), entry=(0, 0.5))
edge(igw, alb, "", "strokeColor=#232F3E;", exit_=(1, 0.5), entry=(0, 0.5))
edge(alb, tgb, "prod :80", "strokeColor=#6c8ebf;fontColor=#6c8ebf;")
edge(alb, tgg, "test :8080", "dashed=1;strokeColor=#82b366;fontColor=#3f8a3f;", pts=[(985, 450), (985, 667)],
     exit_=(1, 0.5), entry=(1, 0.5))
(tb0, tg0, bx0, gx0), (tb1, tg1, bx1, gx1) = tasks          # Per-AZ task IDs and x positions
edge(tgb, tb0, "", "strokeColor=#6c8ebf;", pts=[(bx0 + 24, 597)], exit_=(0, 0.5), entry=(0.5, 0))
edge(tgb, tb1, "", "strokeColor=#6c8ebf;", pts=[(bx1 + 24, 597)], exit_=(1, 0.5), entry=(0.5, 0))
edge(tgg, tg0, "", "dashed=1;strokeColor=#82b366;", pts=[(805, 667), (805, 694)], exit_=(0, 0.5), entry=(1, 0.5))
edge(tgg, tg1, "", "dashed=1;strokeColor=#82b366;", pts=[(1135, 667), (1135, 694)], exit_=(1, 0.5), entry=(0, 0.5))
edge(asg, ecs, "scales", "strokeColor=#E7157B;fontColor=#E7157B;")
vertex("image layers", 1530, 860, 80, 18, "text;html=1;fontSize=11;fontColor=#7AA116;align=right;")  # Edge caption
edge(eps[1], s3, "", "strokeColor=#7AA116;", pts=[(1590, 714), (1590, 854)], exit_=(1, 0.5), entry=(0, 0.5))

note("<b>Security</b><br>• ALB is the only public resource<br>• Tasks: no public IP, private subnets<br>"
     "• No NAT; AWS APIs via endpoints<br>• Managed IAM policies only", 360, 880, 260, 110)
note("<b>Rollback</b><br>• Canary 10% for 5 min, then 100%<br>• Alarm → CodeDeploy stops + rolls back<br>"
     "• Blue kept 5 min for instant switch-back", 1150, 880, 270, 110)

# ---- Write the .drawio file ----
model = (f'<mxGraphModel dx="{W}" dy="{H}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" '
         f'fold="1" page="1" pageScale="1" pageWidth="{W}" pageHeight="{H}" math="0" shadow="0"><root>'
         '<mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(cells) + "</root></mxGraphModel>")  # Diagram model
xml = (f'<mxfile host="app.diagrams.net"><diagram id="onward-architecture" name="Architecture">{model}'
       '</diagram></mxfile>')                               # draw.io file wrapper
OUT_DRAWIO.write_text(xml, encoding="utf-8")                # Save editable source

# ---- Render with draw.io's viewer, then save SVG and PNG ----
tmp = DOCS / "report-src" / "_drawio_view.html"             # Temporary viewer page
cfg = json.dumps({"xml": xml, "highlight": "none", "nav": False, "toolbar": "", "border": 10})  # Viewer config
tmp.write_text(
    '<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#fff}</style></head><body>'
    f'<div class="mxgraph" style="width:{W + 20}px" data-mxgraph="{html.escape(cfg)}"></div>'
    '<script src="https://viewer.diagrams.net/js/viewer-static.min.js"></script>'
    '<pre id="out" style="display:none"></pre><script>'      # Hidden box that receives the serialized SVG
    'const t=setInterval(()=>{const s=document.querySelector(".mxgraph svg");if(!s||!s.querySelector("g g"))return;'
    'clearInterval(t);const c=s.cloneNode(true),r=s.getBoundingClientRect();'  # Copy the rendered diagram
    'c.setAttribute("viewBox",`0 0 ${Math.ceil(r.width)} ${Math.ceil(r.height)}`);'  # Visible drawing area
    'c.setAttribute("width",Math.ceil(r.width));c.setAttribute("height",Math.ceil(r.height));c.removeAttribute("style");'
    'c.style.backgroundColor="#ffffff";'                     # White background
    'document.getElementById("out").textContent=new XMLSerializer().serializeToString(c);},200);'
    '</script></body></html>', encoding="utf-8")
url = tmp.as_uri()                                          # file:// URL
common = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=20000",
          "--run-all-compositor-stages-before-draw"]       # Shared flags
dom = subprocess.run(common + ["--dump-dom", url], capture_output=True, text=True, encoding="utf-8").stdout  # Rendered page
m = re.search(r'<pre id="out"[^>]*>(.*?)</pre>', dom, re.S)  # The serialized SVG (HTML-escaped)
if m and m.group(1).strip():                                # Save the SVG export
    OUT_SVG.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + html.unescape(m.group(1)), encoding="utf-8")
subprocess.run(common + ["--force-device-scale-factor=2", f"--window-size={W + 40},{H + 40}",
                         f"--screenshot={OUT_PNG}", url], capture_output=True)  # PNG picture
tmp.unlink()                                                # Clean up
print("wrote", OUT_DRAWIO.name, OUT_SVG.name if m else "(no svg)", OUT_PNG.name)
