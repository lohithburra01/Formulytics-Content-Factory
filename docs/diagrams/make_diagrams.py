"""Generate the README / framework diagrams in the Formulytics video style.

Style source: OPTIMAL LAP SCRIPTS/raceline_video.py (black canvas, white track edges, dark-grey fill,
grey secondary text, uppercase bold titles, HUD mode colours). Colour carries meaning:
    TOOL  = DEPLOY green     deterministic code decides
    AGENT = SUPERCLIP orange a model decides
    HUMAN = REGEN yellow     the owner decides
    GATE  = BRAKING red      pass/fail check, fails closed

Run:  python docs/diagrams/make_diagrams.py   (writes the .svg files next to this script)
"""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).parent
BG, CARD, EDGE, TRACK = "#000000", "#161616", "#FFFFFF", "#5A5A5A"
GREY1, GREY2 = "#C8C8C8", "#969696"
TAG = {"TOOL": "#3CDC64", "AGENT": "#FF8C00", "HUMAN": "#FFE600", "GATE": "#FF503C"}
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.parts = w, h, []

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=13, fill=GREY1, weight=400, anchor="start", spacing=0):
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
                 f'text-anchor="{anchor}" letter-spacing="{spacing}">{escape(s)}</text>')

    def header(self, title, sub):
        self.text(self.w / 2, 62, title, 30, EDGE, 800, "middle", 2)
        self.text(self.w / 2, 92, sub, 14, GREY1, 500, "middle", 2.5)

    def card(self, x, y, w, h, tag, title, sub=(), edge=EDGE, dash=None, tsize=15):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{CARD}" '
                 f'stroke="{edge}" stroke-width="2.5"{d}/>')
        ty = y + 26
        if tag:
            self.text(x + 16, ty, tag, 11, TAG[tag], 800, spacing=1.5)
            ty += 22
        for line in ([title] if isinstance(title, str) else title):
            self.text(x + 16, ty, line, tsize, EDGE, 800, spacing=1)
            ty += tsize + 4
        ty += 3
        for line in sub:
            self.text(x + 16, ty, line, 12, GREY2, 500)
            ty += 16

    def group(self, x, y, w, h, label):
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="none" '
                 f'stroke="{TRACK}" stroke-width="2"/>')
        self.text(x + 18, y + 26, label, 12, GREY1, 800, spacing=2)

    def path(self, pts, color=TRACK, dash=None, arrow=True, width=4):
        d = "M " + " L ".join(f"{a},{b}" for a, b in pts)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        m = ' marker-end="url(#arr)"' if arrow else ""
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" '
                 f'stroke-linecap="round" stroke-linejoin="round"{da}{m}/>')

    def label(self, x, y, s, fill=GREY2, anchor="middle"):
        self.text(x, y, s, 11, fill, 700, anchor, 1.5)

    def legend(self, y):
        x = 40
        for k, c in TAG.items():
            self.add(f'<circle cx="{x + 7}" cy="{y - 4}" r="7" fill="{c}"/>')
            meaning = {"TOOL": "deterministic code", "AGENT": "a model decides",
                       "HUMAN": "the owner decides", "GATE": "fails closed"}[k]
            self.text(x + 22, y, f"{k}", 11, c, 800, spacing=1.5)
            self.text(x + 22 + len(k) * 11 + 12, y, meaning, 12, GREY2, 500)
            x += 250
        self.text(self.w - 40, y, "@formulytics", 13, GREY2, 800, "end")

    def save(self, name):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
               f'viewBox="0 0 {self.w} {self.h}" font-family="{FONT}">'
               '<defs><marker id="arr" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4.2" '
               'markerHeight="4.2" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#FFFFFF"/>'
               '</marker></defs>'
               f'<rect width="{self.w}" height="{self.h}" rx="28" fill="{BG}"/>'
               + "".join(self.parts) + "</svg>")
        (OUT / name).write_text(svg, encoding="utf-8")


def row(s, x0, y, w, h, gap, items):
    """Cards left to right with track connectors. Returns card boxes."""
    boxes = []
    for i, (tag, title, sub) in enumerate(items):
        x = x0 + i * (w + gap)
        s.card(x, y, w, h, tag, title, sub)
        boxes.append((x, y, w, h))
        if i:
            s.path([(x - gap + 4, y + h / 2), (x - 6, y + h / 2)])
    return boxes


# 1. The framework (README) -------------------------------------------------------------------------
def framework():
    s = Svg(1400, 640)
    s.header("FORMULYTICS RETENTION FRAMEWORK", "DISCOVER A FORMAT ONCE  ·  PRODUCE IT EVERY WEEK")
    s.card(40, 170, 170, 330, "HUMAN", ["PRIVATE", "RULEBOOK"],
           ["the creator's own", "observations on", "retention and", "format fit", "", "never committed,", "read in context", "by both parts"],
           edge=TAG["HUMAN"], dash="8 6")
    s.label(250, 156, "DISCOVER", EDGE, "start")
    d = row(s, 250, 170, 165, 112, 24, [
        ("AGENT", "LANDSCAPE", ["what broadcasters and", "creators already show"]),
        ("TOOL", ["SOURCE", "LIMITS"], ["what the data", "cannot support"]),
        ("AGENT", "ANGLES", ["question + data", "+ visual"]),
        ("HUMAN", "CHECKPOINT", ["owner shortlists;", "vetoes become rules"]),
        ("TOOL", "PROBES", ["cheapest test that", "can kill an angle"]),
        ("GATE", "FREEZE TEST", ["reproduces history,", "deterministic, gated"]),
    ])
    s.label(250, 376, "PRODUCE", EDGE, "start")
    p = row(s, 250, 390, 141, 112, 20.5, [
        ("AGENT", "BRIEF", ["weather, place,", "storylines"]),
        ("TOOL", "NUMBERS", ["blind run,", "bounded knobs"]),
        ("AGENT", ["TOUCH +", "HOOKS"], ["open slots only"]),
        ("GATE", "PRE-FLIGHT", ["rules vs planned", "frames"]),
        ("AGENT", "PREVIEW", ["0-3 s render,", "vision judge"]),
        ("HUMAN", "PICK", ["owner picks;", "gates; publish"]),
        ("TOOL", "SCORE", ["vs real lap and", "real retention"]),
    ])
    x, y, w, h = d[-1]
    s.path([(x + w / 2, y + h + 4), (x + w / 2, 336), (p[0][0] + 110, 336), (p[0][0] + 110, 384)], EDGE)
    s.label(760, 328, "TOOLKIT  ·  FORMAT GRAMMAR  ·  GATES  ·  SKILL.MD", GREY1)
    x, y, w, h = p[-1]
    s.path([(x + w / 2, y + h + 4), (x + w / 2, 548), (p[0][0] + 70, 548), (p[0][0] + 70, y + h + 10)],
           TAG["TOOL"], dash="2 10")
    s.label(760, 540, "LEARN: NEW RULES  ·  VARIANTS  ·  GATES  ·  REGRESSION TESTS", TAG["TOOL"])
    s.path([(212, 226), (244, 226)], TAG["HUMAN"], dash="2 8")
    s.path([(212, 446), (244, 446)], TAG["HUMAN"], dash="2 8")
    s.legend(610)
    s.save("framework.svg")


# 2. The harness (README) ---------------------------------------------------------------------------
def harness():
    s = Svg(1400, 760)
    s.header("THE HARNESS", "ORCHESTRATION  ·  GATES  ·  MEMORY  ·  OBSERVABILITY  ·  COST")
    for i, (t, sub) in enumerate([("FASTAPI", ["POST /runs"]), ("CLI", ["--approve pauses", "before queueing"]),
                                  ("MCP SERVER", ["read · simulate ·", "check; never publish"])]):
        s.card(40, 150 + i * 125, 175, 100, None, t, sub)
    s.path([(217, 200), (262, 200)])
    s.path([(217, 325), (240, 325), (240, 210)], arrow=False)
    s.path([(217, 450), (240, 450), (240, 325)], arrow=False)
    s.card(270, 150, 500, 100, "AGENT", "ORCHESTRATOR",
           ["plans with todos · loads the format's SKILL.md · delegates · strong model"])
    subs = [("RESEARCHER", ["memory, RAG,", "event facts"]), ("SIMULATOR", ["one knob per", "retry, ≤ 3"]),
            ("CRITIC", ["separate model;", "can reject"]), ("PACKAGER", ["caption from", "facts only"])]
    for i, (t, sub) in enumerate(subs):
        x = 270 + i * 130
        s.card(x, 300, 110, 110, "AGENT", t, sub, tsize=12.5)
        s.path([(x + 55, 252), (x + 55, 294)])
    s.group(830, 150, 530, 200, "DETERMINISTIC TOOLKIT  ·  PER FORMAT")
    for i, (t, sub) in enumerate([("ENGINE", ["lap sim, delta", "engine, era cars"]),
                                  ("REALISM", ["speed trace,", "apex, bounds"]),
                                  ("RENDERER", ["fixed look,", "every pixel"])]):
        s.card(850 + i * 168, 196, 152, 134, "TOOL", t, sub)
    s.group(830, 390, 530, 190, "MEMORY")
    for i, (t, sub) in enumerate([("EPISODIC", ["how past runs", "scored"]), ("SEMANTIC", ["knowledge", "graph"]),
                                  ("PROCEDURAL", ["feedback", "rules → gates"]), ("RAG", ["cited; weak", "hits withheld"])]):
        s.card(850 + i * 126, 432, 114, 128, "TOOL", t, sub, tsize=12.5)
    s.path([(772, 330), (824, 330)])
    s.label(800, 322, "CALLS")
    s.path([(772, 390), (800, 390), (800, 470), (824, 470)])
    s.card(270, 470, 240, 100, "GATE", ["8 FAIL-CLOSED", "GATES"], ["a missing artifact fails"])
    s.card(530, 470, 240, 100, "HUMAN", ["PUBLISH", "QUEUE"], ["caption + run manifest"])
    s.path([(715, 412), (715, 440), (390, 440), (390, 464)])
    s.path([(512, 520), (524, 520)])
    s.group(40, 610, 1320, 80, "EVERY RUN")
    s.text(700, 664, "TRACES  ·  APPEND-ONLY LEDGER  ·  RUN MANIFEST  ·  MODEL ROUTING + FALLBACK  ·  BUDGET CAPS  ·  CI ENGINE REGRESSION",
           13, EDGE, 700, "middle", 1.5)
    s.legend(728)
    s.save("harness.svg")


# 3. Discover loop (frameworks/DISCOVER.md) ---------------------------------------------------------
def discover():
    s = Svg(1400, 560)
    s.header("DISCOVER", "FIND A FORMAT WORTH MAKING  ·  STEERED BY THE OWNER")
    s.card(40, 120, 1320, 54, None, "PRIVATE RULEBOOK  ·  READ IN CONTEXT AT EVERY STEP  ·  NEVER COMMITTED",
           edge=TAG["HUMAN"], dash="8 6")
    a = row(s, 40, 210, 310, 112, 26.7, [
        ("AGENT", "1  LANDSCAPE", ["broadcasters, teams, creators, fans:", "who shows what, and the gaps"]),
        ("TOOL", "2  SOURCES", ["capability card per source;", "'cannot support' proved by a probe"]),
        ("AGENT", "3  ANGLES", ["viewer question + data + visual;", "filtered by hard rules"]),
        ("HUMAN", "CHECKPOINT 1", ["keep, kill or redirect;", "a veto with a reason becomes a rule"]),
    ])
    b = row(s, 40, 380, 310, 112, 26.7, [
        ("TOOL", "4  PROBES", ["one lap, one frame, a 5 s mock;", "kill condition stated first"]),
        ("TOOL", "5  PROTOTYPE", ["one full piece, checked against", "an outside reference"]),
        ("HUMAN", "CHECKPOINT 2", ["watched like a viewer;", "approve, rework or kill"]),
        ("GATE", "6  FREEZE", ["toolkit + grammar + gates +", "SKILL.md → Produce"]),
    ])
    x, y, w, h = a[-1]
    s.path([(x + w / 2, y + h + 4), (x + w / 2, 351), (b[0][0] + 155, 351), (b[0][0] + 155, 374)], EDGE)
    s.text(1360, 545, "@formulytics", 13, GREY2, 800, "end")
    s.save("discover.svg")


# 4. Produce loop (frameworks/PRODUCE.md) -----------------------------------------------------------
def produce():
    s = Svg(1400, 560)
    s.header("PRODUCE", "EVERY EVENT  ·  LOCKED BASE  ·  ONE NEW JUDGED TOUCH")
    a = row(s, 40, 130, 244, 120, 25, [
        ("AGENT", "1  BRIEF", ["weather, place, storylines;", "3-5 candidate touches"]),
        ("TOOL", "2  NUMBERS", ["blind, calibrated setup;", "one bounded knob per retry"]),
        ("GATE", "NUMBER GATES", ["realism, apex, trace,", "no inflation"]),
        ("AGENT", "3  DESIGN", ["fill open slots only;", "3 hooks per candidate"]),
        ("GATE", "4  PRE-FLIGHT", ["rulebook vs planned scene", "manifest; no render"]),
    ])
    b = row(s, 40, 330, 244, 120, 25, [
        ("AGENT", "5  PREVIEW", ["render 0-3 s; vision judge", "scores the vlm rules"]),
        ("HUMAN", "6  PICK", ["review packet per variant;", "owner + judge picks logged"]),
        ("GATE", "7  PUBLISH", ["full render; claims gate", "on hooks and caption"]),
        ("TOOL", "8  SCORE", ["vs real lap; vs real 3 s", "hold and watch time"]),
        ("AGENT", "9  LEARN", ["rules, variants, gates,", "tests; owner approves"]),
    ])
    x, y, w, h = a[-1]
    s.path([(x + w / 2, y + h + 4), (x + w / 2, 290), (b[0][0] + 122, 290), (b[0][0] + 122, 324)], EDGE)
    x, y, w, h = a[3]
    s.path([(a[4][0] + 60, y + h + 4), (a[4][0] + 60, 274), (x + w / 2, 274), (x + w / 2, y + h + 8)],
           TAG["GATE"], dash="2 9")
    s.label((a[4][0] + 60 + x + w / 2) / 2, 268, "FAIL → REDESIGN", TAG["GATE"])
    x, y, w, h = b[-1]
    s.path([(x + w / 2, y + h + 4), (x + w / 2, 500), (20, 500), (20, a[0][1] + 60), (34, a[0][1] + 60)],
           TAG["TOOL"], dash="2 10")
    s.label(700, 492, "NEXT EVENT STARTS WITH WHAT THIS ONE TAUGHT", TAG["TOOL"])
    s.legend(540)
    s.save("produce.svg")


if __name__ == "__main__":
    framework(); harness(); discover(); produce()
    print("wrote", sorted(p.name for p in OUT.glob("*.svg")))
