#!/usr/bin/env python3
"""
Gera os cartões SVG do perfil do GitHub (tema roxo escuro com rosa de destaque).

Uso:
    GH_TOKEN=... GH_USER=Luandos python generate_cards.py dist
    python generate_cards.py dist --demo        # dados fictícios, para pré-visualizar

Arquivos gerados em <pasta>:
    overview.svg    resumo (commits, PRs, issues, repositórios, estrelas, seguidores)
    languages.svg   gráfico de rosca com as linguagens mais usadas
    streak.svg      total de contribuições, sequência atual e maior sequência
    activity.svg    gráfico de área com a atividade dos últimos 60 dias
    heatmap.svg     calendário de contribuições com meses e dias da semana
    divider.svg     linha divisória

Usa apenas a biblioteca padrão do Python (nada para instalar).
"""
import datetime as dt
import html
import json
import math
import os
import random
import sys
import urllib.request

# ───────────────────────────── tema ─────────────────────────────
BG0, BG1 = "#0D0221", "#1A0A3D"
LINE = "#3B1A6B"
PURPLE, VIOLET, LILAC = "#A855F7", "#7C3AED", "#D8C7F5"
MUTED = "#9C84C9"
PINK = "#FF2E97"
TILE = "#1A0B38"
TRACK = "#26124D"
FONT = "'Fira Code','JetBrains Mono','SF Mono',ui-monospace,Consolas,'DejaVu Sans Mono',monospace"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
LANG_COLORS = [PURPLE, PINK, VIOLET, "#C084FC", "#F472B6", "#5B21B6"]
HEAT = ["#1D0E3D", "#4C1D95", VIOLET, PURPLE, PINK]
LS1 = 'letter-spacing="1"'
LS12 = 'letter-spacing="1.2"'
DASH = 'stroke-dasharray="3 5"'


# ───────────────────────────── utilidades ─────────────────────────────
def esc(s):
    return html.escape(str(s), quote=True)


def num(n):
    return f"{int(n):,}".replace(",", ".")


def fmt_dm(d):
    return f"{d.day} {MESES[d.month - 1]}"


def fmt_my(d):
    return f"{MESES[d.month - 1]}/{d.year}"


def txt(x, y, s, size=11, fill=LILAC, anchor="start", weight=400, extra=""):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" {extra}>{esc(s)}</text>')


# ───────────────────────────── moldura comum ─────────────────────────────
def frame(w, h, login, path, body, extra_defs="", extra_css=""):
    """Moldura estilo terminal/HUD: grade, linha de varredura, pontos e cantos."""
    title_x = 70
    cursor_x = title_x + len(f"{login}@github:{path}") * 6.62 + 4
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(path)}">
<title>{esc(path)}</title>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>
  <linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{PURPLE}" stop-opacity=".95"/><stop offset=".55" stop-color="{LINE}"/><stop offset="1" stop-color="{PINK}" stop-opacity=".75"/></linearGradient>
  <linearGradient id="gp" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{VIOLET}"/><stop offset=".6" stop-color="{PURPLE}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>
  <linearGradient id="scanG" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{PURPLE}" stop-opacity="0"/><stop offset=".5" stop-color="{PURPLE}" stop-opacity=".09"/><stop offset="1" stop-color="{PURPLE}" stop-opacity="0"/></linearGradient>
  <pattern id="grid" width="22" height="22" patternUnits="userSpaceOnUse"><path d="M22 0H0V22" fill="none" stroke="{PURPLE}" stroke-opacity=".07"/></pattern>
  <filter id="glow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <clipPath id="clip"><rect width="{w}" height="{h}" rx="14"/></clipPath>
  {extra_defs}
</defs>
<style>
  text{{font-family:{FONT}}}
  .in{{animation:in .7s ease-out both}}
  @keyframes in{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
  .grow{{transform-box:fill-box;transform-origin:left center;animation:grow 1.1s cubic-bezier(.2,.8,.2,1) both}}
  @keyframes grow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
  .draw{{stroke-dasharray:1000;animation:draw 2.2s ease-out both}}
  @keyframes draw{{from{{stroke-dashoffset:1000}}to{{stroke-dashoffset:0}}}}
  .blink{{animation:blink 1.1s steps(1) infinite}}
  @keyframes blink{{50%{{opacity:0}}}}
  .pulse{{animation:pulse 2.6s ease-in-out infinite}}
  @keyframes pulse{{50%{{opacity:.35}}}}
  .scan{{animation:scan 7s linear infinite}}
  @keyframes scan{{from{{transform:translateY(-50px)}}to{{transform:translateY({h}px)}}}}
  @media (prefers-reduced-motion:reduce){{.in,.grow,.draw,.seg,.ring,.scan{{animation:none!important}}}}
  {extra_css}
</style>
<g clip-path="url(#clip)">
  <rect width="{w}" height="{h}" fill="url(#bg)"/>
  <rect width="{w}" height="{h}" fill="url(#grid)"/>
  <rect class="scan" width="{w}" height="50" fill="url(#scanG)"/>
  <circle cx="20" cy="17" r="4.5" fill="{PINK}"/><circle cx="36" cy="17" r="4.5" fill="{PURPLE}"/><circle cx="52" cy="17" r="4.5" fill="{LINE}"/>
  {txt(title_x, 21, f"{login}@github:{path}", 11, MUTED)}
  <rect class="blink" x="{cursor_x:.1f}" y="10" width="7" height="13" fill="{PURPLE}"/>
  <circle class="pulse" cx="{w - 66}" cy="17" r="3.5" fill="{PINK}"/>
  {txt(w - 20, 21, "online", 10, MUTED, "end")}
  <line x1="0" y1="34" x2="{w}" y2="34" stroke="{LINE}" stroke-opacity=".8"/>
  {body}
</g>
<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="13.5" fill="none" stroke="url(#bd)" stroke-width="1.5"/>
<path d="M12 {h - 26} V{h - 12} H26 M{w - 12} {h - 26} V{h - 12} H{w - 26}" fill="none" stroke="{PINK}" stroke-opacity=".85" stroke-width="1.5"/>
</svg>
'''


# ───────────────────────────── cartão: resumo ─────────────────────────────
def card_overview(d):
    w, h = 440, 232
    tiles = [("COMMITS", d["commits"]), ("PULL REQUESTS", d["prs"]), ("ISSUES", d["issues"]),
             ("REPOSITÓRIOS", d["repos"]), ("ESTRELAS", d["stars"]), ("SEGUIDORES", d["followers"])]
    tw, th, gap = 128, 68, 10
    out = []
    for i, (label, value) in enumerate(tiles):
        x = 18 + (i % 3) * (tw + gap)
        y = 54 + (i // 3) * (th + gap)
        out.append(
            f'<g class="in" style="animation-delay:{.15 + i * .09:.2f}s">'
            f'<rect x="{x}" y="{y}" width="{tw}" height="{th}" rx="9" fill="{TILE}" stroke="{LINE}"/>'
            f'<rect x="{x}" y="{y + 12}" width="3" height="{th - 24}" rx="1.5" fill="{PINK if i == 0 else PURPLE}"/>'
            f'{txt(x + 14, y + 23, label, 9.5, MUTED, extra=LS1)}'
            f'{txt(x + 14, y + 52, num(value), 24, "url(#gp)" if i == 0 else LILAC, weight=700)}'
            f'</g>')
    since = d["created"]
    out.append(f'<g class="in" style="animation-delay:.9s">'
               f'{txt(w / 2, 220, f"membro desde {fmt_my(since)}", 10, MUTED, "middle")}</g>')
    return frame(w, h, d["login"], "~/resumo", "\n".join(out))


# ───────────────────────────── cartão: linguagens ─────────────────────────────
def card_languages(d):
    w, h = 440, 232
    langs = d["languages"]  # lista de (nome, bytes) já ordenada
    total = sum(b for _, b in langs)
    if total <= 0:
        body = txt(w / 2, 140, "sem linguagens detectadas ainda", 12, MUTED, "middle")
        return frame(w, h, d["login"], "~/linguagens", body)

    top = langs[:5]
    rest = sum(b for _, b in langs[5:])
    if rest > 0:
        top.append(("Outras", rest))

    cx, cy, r, sw = 104, 138, 54, 16
    circ = 2 * math.pi * r
    gap = 2.5 if len(top) > 1 else 0
    css, ring, legend = [], [], []
    acc = 0.0
    for i, (name, b) in enumerate(top):
        frac = b / total
        length = max(circ * frac - gap, 0.6)
        color = LANG_COLORS[i % len(LANG_COLORS)]
        css.append(f"@keyframes s{i}{{from{{stroke-dasharray:0 {circ:.2f}}}to{{stroke-dasharray:{length:.2f} {circ - length:.2f}}}}}"
                   f".s{i}{{animation:s{i} 1.2s {0.2 + i * .15:.2f}s cubic-bezier(.2,.8,.2,1) both}}")
        ring.append(f'<circle class="seg s{i}" cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
                    f'stroke-width="{sw}" stroke-dasharray="{length:.2f} {circ - length:.2f}" '
                    f'stroke-dashoffset="{-acc:.2f}" transform="rotate(-90 {cx} {cy})"/>')
        acc += circ * frac

        ly = 64 + i * 26
        bar_w = 206 * frac
        legend.append(
            f'<g class="in" style="animation-delay:{.3 + i * .1:.2f}s">'
            f'<rect x="200" y="{ly - 9}" width="9" height="9" rx="2" fill="{color}"/>'
            f'{txt(216, ly, name, 11, LILAC)}'
            f'{txt(422, ly, f"{frac * 100:.1f}%", 11, MUTED, "end")}'
            f'<rect x="216" y="{ly + 6}" width="206" height="4" rx="2" fill="{TRACK}"/>'
            f'<rect class="grow" style="animation-delay:{.45 + i * .1:.2f}s" x="216" y="{ly + 6}" '
            f'width="{max(bar_w, 3):.1f}" height="4" rx="2" fill="{color}"/>'
            f'</g>')

    center = (f'<circle cx="{cx}" cy="{cy}" r="{r - sw / 2 - 6}" fill="{TILE}" fill-opacity=".7"/>'
              f'{txt(cx, cy + 4, len(langs), 22, LILAC, "middle", 700)}'
              f'{txt(cx, cy + 20, "linguagens" if len(langs) != 1 else "linguagem", 8.5, MUTED, "middle")}')
    body = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{TRACK}" stroke-width="{sw}"/>' + \
           "\n".join(ring) + center + "\n".join(legend)
    return frame(w, h, d["login"], "~/linguagens", body, extra_css="\n".join(css))


# ───────────────────────────── cartão: sequência ─────────────────────────────
def card_streak(d):
    w, h = 900, 196
    s = d["streaks"]
    r = 46
    circ = 2 * math.pi * r
    frac = min(s["current"] / max(s["longest"], 1), 1) if s["current"] else 0
    end_off = circ * (1 - frac)
    css = (f"@keyframes rg{{from{{stroke-dashoffset:{circ:.2f}}}to{{stroke-dashoffset:{end_off:.2f}}}}}"
           f".ring{{animation:rg 1.6s .3s cubic-bezier(.2,.8,.2,1) both}}")

    def rng(a, b):
        if not a:
            return "sem sequência ainda"
        return fmt_dm(a) if a == b else f"{fmt_dm(a)} - {fmt_dm(b)}"

    first = d["first_day"]
    seps = "".join(f'<line x1="{x}" y1="60" x2="{x}" y2="168" stroke="{LINE}" stroke-dasharray="2 5"/>' for x in (300, 600))
    left = (f'<g class="in" style="animation-delay:.15s">'
            f'{txt(150, 114, num(d["total"]), 40, LILAC, "middle", 700)}'
            f'{txt(150, 138, f"desde {fmt_my(first)}", 10.5, MUTED, "middle")}'
            f'{txt(150, 176, "TOTAL DE CONTRIBUIÇÕES", 10, PURPLE, "middle", extra=LS12)}</g>')
    mid = (f'<g class="in" style="animation-delay:.3s">'
           f'<circle cx="450" cy="106" r="{r}" fill="none" stroke="{TRACK}" stroke-width="7"/>'
           f'<circle class="ring" cx="450" cy="106" r="{r}" fill="none" stroke="url(#gp)" stroke-width="7" '
           f'stroke-linecap="round" stroke-dasharray="{circ:.2f}" stroke-dashoffset="{end_off:.2f}" '
           f'transform="rotate(-90 450 106)" filter="url(#glow)"/>'
           f'{txt(450, 114, s["current"], 32, LILAC, "middle", 700)}'
           f'{txt(450, 130, "dias" if s["current"] != 1 else "dia", 9.5, MUTED, "middle")}'
           f'{txt(450, 176, "SEQUÊNCIA ATUAL", 10, PINK, "middle", extra=LS12)}</g>')
    right = (f'<g class="in" style="animation-delay:.45s">'
             f'<text x="750" y="114" font-size="40" fill="{LILAC}" text-anchor="middle" font-weight="700">{s["longest"]}'
             f'<tspan font-size="13" fill="{MUTED}" font-weight="400"> {"dias" if s["longest"] != 1 else "dia"}</tspan></text>'
             f'{txt(750, 138, rng(s["longest_start"], s["longest_end"]), 10.5, MUTED, "middle")}'
             f'{txt(750, 176, "MAIOR SEQUÊNCIA", 10, PURPLE, "middle", extra=LS12)}</g>')
    return frame(w, h, d["login"], "~/sequencia", seps + left + mid + right, extra_css=css)


# ───────────────────────────── cartão: atividade ─────────────────────────────
def smooth_path(pts, lo, hi):
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1x, c1y = p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6
        c2x, c2y = p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6
        c1y, c2y = min(max(c1y, lo), hi), min(max(c2y, lo), hi)
        d += f" C{c1x:.1f},{c1y:.1f} {c2x:.1f},{c2y:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def card_activity(d, n=60):
    w, h = 900, 276
    days = d["days"]
    today = d["today"]
    series = [(today - dt.timedelta(days=n - 1 - i)) for i in range(n)]
    counts = [days.get(x, 0) for x in series]
    total = sum(counts)
    maxc = max(counts) if counts else 0
    ymax = max(4, int(math.ceil(maxc / 4.0)) * 4)

    x0, x1, y0, y1 = 56, 868, 88, 238
    step = (x1 - x0) / (n - 1)
    pts = [(x0 + i * step, y1 - (c / ymax) * (y1 - y0)) for i, c in enumerate(counts)]

    defs = (f'<linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{PURPLE}" stop-opacity=".5"/>'
            f'<stop offset="1" stop-color="{PURPLE}" stop-opacity="0"/></linearGradient>')

    grid = []
    for k in range(5):
        gy = y1 - k * (y1 - y0) / 4
        grid.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" stroke="{LINE}" stroke-opacity="{.9 if k == 0 else .45}" '
                    f'{"" if k == 0 else DASH}/>')
        grid.append(txt(x0 - 10, gy + 3.5, int(k * ymax / 4), 9.5, MUTED, "end"))

    labels = []
    for i in list(range(0, n, 10)) + [n - 1]:
        if i == n - 1 and (n - 1) % 10 < 4 and (n - 1) % 10 != 0:
            continue
        anchor = "end" if i == n - 1 else ("start" if i == 0 else "middle")
        labels.append(txt(pts[i][0], y1 + 20, fmt_dm(series[i]), 9.5, MUTED, anchor))

    line = smooth_path(pts, y0, y1)
    area = f"{line} L{x1:.1f},{y1} L{x0:.1f},{y1} Z"
    dots = "".join(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.6" fill="{LILAC}" stroke="{BG0}" stroke-width="1"/>'
                   for (px, py), c in zip(pts, counts) if c > 0)

    peak = ""
    if maxc > 0:
        pi = counts.index(maxc)
        px, py = pts[pi]
        label = f"pico: {maxc}"
        bw = len(label) * 6.4 + 14
        bx = min(max(px - bw / 2, x0), x1 - bw)
        peak = (f'<g class="in" style="animation-delay:1.6s">'
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="{PINK}" filter="url(#glow)"/>'
                f'<rect x="{bx:.1f}" y="{py - 30:.1f}" width="{bw:.1f}" height="19" rx="5" fill="{TILE}" stroke="{PINK}" stroke-opacity=".8"/>'
                f'{txt(bx + bw / 2, py - 17, label, 10, LILAC, "middle")}</g>')

    summary = (f'<text x="{x0}" y="62" font-size="11" fill="{MUTED}">contribuições nos últimos {n} dias: '
               f'<tspan fill="{LILAC}" font-weight="700">{num(total)}</tspan></text>')
    body = (summary + "".join(grid) + "".join(labels) +
            f'<path class="in" style="animation-delay:.6s" d="{area}" fill="url(#area)"/>'
            f'<path class="draw" pathLength="1000" d="{line}" fill="none" stroke="url(#gp)" stroke-width="2.6" '
            f'stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)"/>'
            f'<g class="in" style="animation-delay:1.4s">{dots}</g>' + peak)
    return frame(w, h, d["login"], "~/atividade", body, extra_defs=defs)


# ───────────────────────────── cartão: calendário ─────────────────────────────
def card_heatmap(d):
    w, h = 900, 214
    days = d["days"]
    today = d["today"]
    pitch, cell = 15, 12
    x0, y0 = 54, 62
    sunday_idx = (today.weekday() + 1) % 7
    start = today - dt.timedelta(days=sunday_idx + 52 * 7)
    cols = 53

    window = [days.get(start + dt.timedelta(days=i), 0) for i in range((today - start).days + 1)]
    maxc = max(window) if window else 0
    total = sum(window)

    def level(c):
        if c <= 0 or maxc <= 0:
            return 0
        q = c / maxc
        return 1 if q <= .25 else 2 if q <= .5 else 3 if q <= .75 else 4

    groups, months = [], []
    last_label_col, last_month = -10, None
    for cidx in range(cols):
        first = start + dt.timedelta(days=cidx * 7)
        if first.month != last_month:
            if cidx - last_label_col >= 3:
                months.append(txt(x0 + cidx * pitch, y0 - 10, MESES[first.month - 1], 9.5, MUTED))
                last_label_col = cidx
            last_month = first.month
        cells = []
        for r in range(7):
            day = first + dt.timedelta(days=r)
            if day > today:
                break
            c = days.get(day, 0)
            lv = level(c)
            extra = ' filter="url(#glow)"' if lv == 4 else ""
            edge = "" if lv else ' stroke="' + LINE + '" stroke-opacity=".35"'
            cells.append(f'<rect x="{x0 + cidx * pitch}" y="{y0 + r * pitch}" width="{cell}" height="{cell}" rx="3" '
                         f'fill="{HEAT[lv]}"{edge}{extra}/>')
        groups.append(f'<g class="in" style="animation-delay:{.1 + cidx * .028:.3f}s">{"".join(cells)}</g>')

    wk = "".join(txt(x0 - 10, y0 + r * pitch + 10, name, 9.5, MUTED, "end")
                 for r, name in ((1, "seg"), (3, "qua"), (5, "sex")))
    ly = y0 + 7 * pitch + 22
    legend_x = x0 + cols * pitch - 3 - (5 * 15 + 70)
    legend = (txt(legend_x, ly + 9, "menos", 9.5, MUTED) +
              "".join(f'<rect x="{legend_x + 40 + i * 15}" y="{ly}" width="12" height="12" rx="3" fill="{HEAT[i]}" stroke="{LINE}" stroke-opacity=".5"/>' for i in range(5)) +
              txt(legend_x + 40 + 5 * 15 + 4, ly + 9, "mais", 9.5, MUTED))
    summary = (f'<text x="{x0}" y="{ly + 9}" font-size="11" fill="{MUTED}">'
               f'<tspan fill="{LILAC}" font-weight="700">{num(total)}</tspan> contribuições no último ano</text>')
    return frame(w, h, d["login"], "~/calendario", "".join(months) + wk + "".join(groups) + summary + legend)


# ───────────────────────────── divisória ─────────────────────────────
def divider():
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="14" viewBox="0 0 900 14" role="presentation">
<defs>
  <linearGradient id="l" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{PURPLE}" stop-opacity="0"/><stop offset=".25" stop-color="{VIOLET}"/><stop offset=".5" stop-color="{PURPLE}"/><stop offset=".75" stop-color="{VIOLET}"/><stop offset="1" stop-color="{PURPLE}" stop-opacity="0"/></linearGradient>
  <filter id="g" x="-50%" y="-300%" width="200%" height="700%"><feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<rect x="0" y="6" width="900" height="2" fill="url(#l)" filter="url(#g)"/>
<rect x="445" y="3" width="8" height="8" transform="rotate(45 449 7)" fill="{PINK}" filter="url(#g)"/>
</svg>
'''


# ───────────────────────────── dados ─────────────────────────────
def gql(query, variables, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-cards"},
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        data = json.load(resp)
    if data.get("errors"):
        raise RuntimeError(json.dumps(data["errors"], ensure_ascii=False))
    return data["data"]


def parse_dt(s):
    return dt.datetime.strptime(s[:10], "%Y-%m-%d").date()


def streaks(days):
    if not days:
        return dict(current=0, longest=0, longest_start=None, longest_end=None)
    ordered = sorted(days)
    today = ordered[-1]
    one = dt.timedelta(days=1)

    cur, d = 0, today
    if days.get(d, 0) == 0:  # o dia de hoje ainda não acabou: não quebra a sequência
        d -= one
    while days.get(d, 0) > 0:
        cur += 1
        d -= one

    best, best_s, best_e = 0, None, None
    run, run_s, prev = 0, None, None
    for day in ordered:
        if days[day] > 0:
            if run and prev is not None and day - prev == one:
                run += 1
            else:
                run, run_s = 1, day
            if run > best:
                best, best_s, best_e = run, run_s, day
        else:
            run = 0
        prev = day
    return dict(current=cur, longest=best, longest_start=best_s, longest_end=best_e)


def fetch(login, token):
    base = gql("""
    query($login:String!){ user(login:$login){
      createdAt
      followers{totalCount}
      pullRequests{totalCount}
      issues{totalCount}
      repositories(ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC, first:100){
        totalCount
        nodes{ stargazerCount
          languages(first:8, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name } } } }
      }
    } }""", {"login": login}, token)["user"]

    created = parse_dt(base["createdAt"])
    now = dt.datetime.now(dt.timezone.utc)
    blocks = []
    for y in range(created.year, now.year + 1):
        a = f"{y}-01-01T00:00:00Z"
        b = min(now, dt.datetime(y, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
        blocks.append(f'y{y}: contributionsCollection(from:"{a}", to:"{b}"){{ totalCommitContributions '
                      f'contributionCalendar{{ weeks{{ contributionDays{{ date contributionCount }} }} }} }}')
    contrib = gql("query($login:String!){ user(login:$login){ " + " ".join(blocks) + " } }",
                  {"login": login}, token)["user"]

    days, commits = {}, 0
    for block in contrib.values():
        commits += block["totalCommitContributions"]
        for week in block["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                days[parse_dt(day["date"])] = day["contributionCount"]

    langs = {}
    stars = 0
    for repo in base["repositories"]["nodes"]:
        stars += repo["stargazerCount"]
        for edge in repo["languages"]["edges"]:
            langs[edge["node"]["name"]] = langs.get(edge["node"]["name"], 0) + edge["size"]

    return dict(login=login, created=created, followers=base["followers"]["totalCount"],
                prs=base["pullRequests"]["totalCount"], issues=base["issues"]["totalCount"],
                repos=base["repositories"]["totalCount"], stars=stars, commits=commits,
                days=days, languages=sorted(langs.items(), key=lambda kv: -kv[1]))


def demo(login):
    rnd = random.Random(7)
    today = dt.date(2026, 10, 26)
    days = {}
    for i in range(0, 400):
        day = today - dt.timedelta(days=i)
        recent = i < 140
        p = .55 if recent else .12
        days[day] = rnd.choice([1, 1, 2, 3, 4, 6, 9]) if rnd.random() < p else 0
    days[today] = 0
    return dict(login=login, created=dt.date(2025, 7, 3), followers=1, prs=4, issues=0, repos=5, stars=0,
                commits=sum(days.values()) - 12, days=days,
                languages=[("Python", 61200), ("C", 32800), ("JavaScript", 9100), ("HTML", 5200), ("CSS", 2100), ("Shell", 900)])


def main():
    out = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "dist"
    login = os.environ.get("GH_USER", "Luandos")
    data = demo(login) if "--demo" in sys.argv else fetch(login, os.environ["GH_TOKEN"])
    data["today"] = max(data["days"]) if data["days"] else dt.date.today()
    data["first_day"] = data["created"]
    data["total"] = sum(data["days"].values())
    data["streaks"] = streaks(data["days"])
    data["login"] = data["login"].lower()

    os.makedirs(out, exist_ok=True)
    files = {"overview.svg": card_overview(data), "languages.svg": card_languages(data),
             "streak.svg": card_streak(data), "activity.svg": card_activity(data),
             "heatmap.svg": card_heatmap(data), "divider.svg": divider()}
    for name, svg in files.items():
        with open(os.path.join(out, name), "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"ok  {name}  {len(svg) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
