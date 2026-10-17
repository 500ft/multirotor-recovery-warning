"""Shared figure settings for the plotting scripts in Analysis/.

One place for the font ladder, tick and legend defaults, entity colours and
deterministic file output, so every committed figure follows the same rules.
Plotting only: nothing here touches a computed value.
"""
from contextlib import contextmanager
from pathlib import Path

import matplotlib
from matplotlib.colors import to_rgb

# Three font sizes by role: titles, axis labels and series names; legends and
# annotations; tick labels. Panel letters are the only larger text.
BASE, SMALL, TICK = 10, 9, 8
LETTER = 12

INK = '#222222'
GRAY = '#62676d'
LIGHT = '#d6d9dc'

# One colour per entity, reused in every figure that shows that entity.
# Parameter tiers are ordered, so they share one hue at three depths.
TIER = {'best': '#00441b', 'nominal': '#238b45', 'worst': '#74c476'}
# Design packages in the survivable-set study (Okabe-Ito, no red/green pair).
ACTION = {'realloc_only': '#0072B2', 'mechanism': '#E69F00', 'parachute': '#CC79A7'}
ACTION_NAME = {'realloc_only': 'Thrust reallocation only',
               'mechanism': 'Guard mechanism',
               'parachute': 'Parachute-like device'}
FAILURE_NAME = {'one_out': 'One rotor out',
                'partial_authority': 'Partial authority (60%)',
                'two_adjacent': 'Two adjacent rotors out',
                'two_opposite': 'Two opposite rotors out'}
# QDrone2 channels and command directions, as chosen in PR #60.
QDRONE = {'altitude': '#2980b9', 'voltage': '#27ae60', 'reference': GRAY,
          'up': '#2980b9', 'down': '#7d3c98'}

RC = {
    'font.size': BASE, 'axes.titlesize': BASE, 'axes.labelsize': BASE,
    'legend.fontsize': SMALL, 'legend.title_fontsize': SMALL,
    'xtick.labelsize': TICK, 'ytick.labelsize': TICK,
    'figure.titlesize': BASE, 'figure.labelsize': BASE,
    'axes.titlelocation': 'left', 'axes.titleweight': 'normal', 'axes.titlepad': 6,
    'xtick.direction': 'out', 'ytick.direction': 'out',
    'axes.spines.top': False, 'axes.spines.right': False,
    'axes.edgecolor': '#80858a', 'axes.labelcolor': INK, 'text.color': INK,
    'xtick.color': INK, 'ytick.color': INK,
    'axes.grid': False, 'grid.color': LIGHT, 'grid.linewidth': .6,
    'legend.frameon': False,
    'figure.facecolor': 'white', 'axes.facecolor': 'white',
    'savefig.facecolor': 'white', 'savefig.dpi': 300,
    'pdf.fonttype': 42,
}


@contextmanager
def style():
    """Apply the shared settings for the duration of one figure."""
    with matplotlib.rc_context(RC):
        yield


def tint(color, amount=.35):
    """Mix a colour with white; amount=1 keeps the colour, 0 gives white."""
    r, g, b = to_rgb(color)
    return (1 - amount + amount*r, 1 - amount + amount*g, 1 - amount + amount*b)


def panel_letter(fig, ax, letter, dx=-.06, dy=.02):
    """Bold panel letter just outside the top-left corner of an axes."""
    box = ax.get_position()
    fig.text(box.x0 + dx, box.y1 + dy, letter, fontsize=LETTER,
             fontweight='bold', ha='left', va='bottom')


def save(fig, path, formats=('png',)):
    """Write a 300-dpi PNG and any vector copies without timestamps."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    for ext in formats:
        out = path.with_suffix('.' + ext)
        if ext == 'pdf':
            fig.savefig(out, metadata={'CreationDate': None, 'ModDate': None})
        else:
            fig.savefig(out, dpi=300)


# ---------------------------------------------------------------------------
# Data-only canvas rules (figures/v6). Used by the rebuilt NanoBench replay and
# survivable-set figures. The settings above stay for the QDrone2 and
# release-recovery generators, which need data that is not committed.
#
# - The canvas carries data, axes, tick labels, axis labels, panel letters and
#   one framed legend. Everything in words lives in <stem>.caption.md beside
#   the image and in the document under it.
# - Condition (which series) is carried by marker shape and line style; state
#   by marker fill. Colour appears only in a heatmap field with a colourbar.
# - Nothing printed may touch anything: ``audit`` lists every pair that does,
#   and ``save_audited`` refuses to write while the list is not empty.
# - Type is Computer Modern (matplotlib's bundled cmr10).
# ---------------------------------------------------------------------------
from matplotlib.text import Text  # noqa: E402

RULE_INK = 'black'
FILL = {True: RULE_INK, False: 'white'}
MARKER = {'ms': 5, 'mew': 0.9, 'color': RULE_INK}
LINE = {'color': RULE_INK, 'lw': 0.9}
DASHED = (0, (4, 3))
LABEL_SIZE, LETTER_SIZE, TICK_SIZE = 9, 9, 7
DPI = 600


def apply() -> None:
    matplotlib.rcParams.update({
        'font.family': 'serif',
        'font.serif': ['cmr10'],
        'mathtext.fontset': 'cm',
        # cmr10 has no Unicode minus; mathtext tick labels carry a proper one.
        'axes.formatter.use_mathtext': True,
        'axes.unicode_minus': False,
        'font.size': LABEL_SIZE,
        'axes.labelsize': LABEL_SIZE,
        'legend.fontsize': LABEL_SIZE,
        'xtick.labelsize': TICK_SIZE,
        'ytick.labelsize': TICK_SIZE,
        'xtick.direction': 'out',
        'ytick.direction': 'out',
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.linewidth': 0.8,
        'axes.edgecolor': RULE_INK,
        'axes.labelcolor': RULE_INK,
        'text.color': RULE_INK,
        'xtick.color': RULE_INK,
        'ytick.color': RULE_INK,
        'axes.grid': False,
        'legend.frameon': True,
        'legend.fancybox': False,
        'legend.edgecolor': RULE_INK,
        'legend.framealpha': 1.0,
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'savefig.facecolor': 'white',
        'savefig.dpi': DPI,
    })


def letter(ax, text: str) -> None:
    """Panel letter just above the top-left corner of an axes."""
    ax.text(0, 1.04, text, transform=ax.transAxes, ha='left', va='bottom', size=LETTER_SIZE)


def audit(fig) -> list:
    """Pairs of printed things whose boxes touch. Empty means the canvas is clean.

    Every drawn text (tick labels inside the view, axis labels, panel letters,
    legend entries, heatmap cell numbers) is checked against every other drawn
    text, against the lines drawn in each axes and against each legend frame.
    Data is not checked against data. Texts inside a legend are not checked
    against their own frame.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    legends = list(fig.legends) + [ax.get_legend() for ax in fig.axes if ax.get_legend()]
    owner = {id(child): legend for legend in legends for child in legend.findobj()}
    tick_labels, drawn = set(), []
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            low, high = sorted(axis.get_view_interval())
            slack = 1e-9 * (high - low)
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                for label in (tick.label1, tick.label2):
                    tick_labels.add(id(label))
                    if (label.get_visible() and label.get_text().strip()
                            and low - slack <= tick.get_loc() <= high + slack):
                        drawn.append(label)
    drawn += [t for t in fig.findobj(Text)
              if id(t) not in tick_labels and t.get_visible() and t.get_text().strip()]
    texts = [(f'text {t.get_text()!r}', t.get_window_extent(renderer).padded(1), owner.get(id(t)))
             for t in drawn]
    others = [(f"data in {ax.get_ylabel() or 'axes'}", line.get_window_extent(renderer), None)
              for ax in fig.axes for line in ax.lines]
    others += [('legend frame', legend.get_window_extent(renderer), legend) for legend in legends]
    hits = []
    for i, (name_a, box_a, legend_a) in enumerate(texts):
        for name_b, box_b, legend_b in texts[i + 1:] + others:
            if legend_a is not None and legend_a is legend_b:
                continue
            if box_a.overlaps(box_b):
                hits.append((name_a, name_b))
    return hits


def save_audited(fig, stem, formats=('png',)) -> None:
    """Write ``stem.<ext>`` for each format without timestamps; refuse a touching canvas."""
    hits = audit(fig)
    if hits:
        raise ValueError(f'printed items touch: {hits}')
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    for ext in formats:
        fig.savefig(stem.with_suffix(f'.{ext}'), dpi=DPI,
                    metadata={'CreationDate': None, 'ModDate': None} if ext == 'pdf' else {})
