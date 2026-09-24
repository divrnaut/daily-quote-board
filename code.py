# Daily Quote Board for the Adafruit MatrixPortal M4 (64x32 RGB matrix).
#
# Picks a quote and color pair from /quotes.json and /colors.json once a day,
# reveals it letter by letter (paging long quotes), plays a short loading
# animation, and repeats. The display turns off overnight.
#
# Settings and the main loop live here; everything else is in helpers.py.
# Based loosely on https://learn.adafruit.com/aio-quote-board-matrix-display

import time

import displayio
import terminalio

from adafruit_matrixportal.matrixportal import MatrixPortal
from adafruit_ticks import ticks_ms, ticks_diff

import helpers

# --- Settings ---

QUOTES_FILE = "/quotes.json"
COLORS_FILE = "/colors.json"

# IANA timezone; Adafruit IO handles daylight saving.
TIME_LOCATION = "America/Los_Angeles"

# Local hour (24h) when the next day's quote is picked.
DAY_ROLLOVER_HOUR = 6

# Display is off from this hour until DAY_ROLLOVER_HOUR.
NIGHT_START_HOUR = 21
NIGHT_CHECK_INTERVAL_SECONDS = 60

# How long to show the quote before the animation. Pages repeat until time
# runs out, but a pass is only started if the whole thing fits.
QUOTE_DISPLAY_SECONDS = 2 * 60

PAGE_HOLD_SECONDS = 3
ATTRIBUTION_HOLD_SECONDS = 2

# Letters slide in from the right one at a time, typewriter style.
LETTER_SLIDE_STAGGER = 0.03       # delay between letters starting
LETTER_SLIDE_DURATION = 0.3       # time for one letter to land
LETTER_SLIDE_START_OFFSET = 10    # starting distance (px) right of its spot
LETTER_SLIDE_FRAME_DELAY = 0.02   # time between redraws

# 64x32 BMPs for the loading animation.
ANIMATION_FRAMES = (
    "/frames/frame1.bmp",
    "/frames/frame2.bmp",
    "/frames/frame3.bmp",
)
ANIMATION_FRAME_DELAY = 0.8
ANIMATION_LOOPS = 5

# No battery-backed clock, so resync periodically. Keep under ~3 days
# (the limit of the ms tick counter).
TIME_RESYNC_SECONDS = 60 * 60

# Used only if colors.json can't be loaded.
QUOTE_COLOR = 0xFFFFFF
SOURCE_COLOR = 0xFFA000

# terminalio.FONT is ~6x8 px: about 10 chars x 3 lines.
FONT = terminalio.FONT
LINE_HEIGHT = 9

# Pixels hidden by the case bezel on each side.
PADDING_LEFT = 3
PADDING_RIGHT = 0
PADDING_TOP = 0
PADDING_BOTTOM = 0


# --- Setup ---

matrixportal = MatrixPortal(width=64, height=32, bit_depth=4, debug=False)
display = matrixportal.display

VISIBLE_WIDTH = display.width - PADDING_LEFT - PADDING_RIGHT
VISIBLE_HEIGHT = display.height - PADDING_TOP - PADDING_BOTTOM
# No extra margin: glyphs already include a blank column on the right.
TEXT_MAX_WIDTH = max(1, VISIBLE_WIDTH)
MAX_LINES_PER_PAGE = max(1, VISIBLE_HEIGHT // LINE_HEIGHT)

root_group = displayio.Group()
root_group.x = PADDING_LEFT
root_group.y = PADDING_TOP
try:
    display.root_group = root_group
except AttributeError:
    # CircuitPython 8.x and earlier
    display.show(root_group)

screen = helpers.QuoteScreen(
    display,
    root_group,
    font=FONT,
    line_height=LINE_HEIGHT,
    visible_height=VISIBLE_HEIGHT,
    slide_start_offset=LETTER_SLIDE_START_OFFSET,
    slide_stagger=LETTER_SLIDE_STAGGER,
    slide_duration=LETTER_SLIDE_DURATION,
    slide_frame_delay=LETTER_SLIDE_FRAME_DELAY,
)


# --- Quotes and colors ---

QUOTES = helpers.load_quotes(QUOTES_FILE)
print("Loaded {} quotes".format(len(QUOTES)))

try:
    COLORS = helpers.load_colors(COLORS_FILE)
    print("Loaded {} colors".format(len(COLORS)))
except Exception as e:
    print("Could not load colors.json ({}), falling back to fixed colors.".format(e))
    COLORS = [("default_quote", QUOTE_COLOR), ("default_source", SOURCE_COLOR)]


# --- Main loop ---

def pages_for_date(date_tuple):
    """Pick the quote and colors for a date and split it into pages."""
    quote_text, author, source = QUOTES[helpers.quote_index_for_date(date_tuple, len(QUOTES))]
    attribution = helpers.format_attribution(author, source)

    quote_color_idx, source_color_idx = helpers.colors_for_date(date_tuple, len(COLORS))
    quote_color_name, quote_color_value = COLORS[quote_color_idx]
    source_color_name, source_color_value = COLORS[source_color_idx]

    print(
        "Today's quote ({}): {} - {} [{} / {}]".format(
            date_tuple, quote_text, attribution, quote_color_name, source_color_name
        )
    )
    return helpers.paginate_quote(
        quote_text,
        attribution,
        quote_color_value,
        source_color_value,
        font=FONT,
        max_width=TEXT_MAX_WIDTH,
        max_lines=MAX_LINES_PER_PAGE,
        page_hold_seconds=PAGE_HOLD_SECONDS,
        attribution_hold_seconds=ATTRIBUTION_HOLD_SECONDS,
    )


def set_brightness(level):
    """Not every display supports brightness, so failures are ignored."""
    try:
        display.brightness = level
    except Exception:
        pass


def main():
    helpers.sync_time(matrixportal.network, TIME_LOCATION)
    last_resync = ticks_ms()

    current_date = None
    current_pages = None
    is_dark = False

    while True:
        if ticks_diff(ticks_ms(), last_resync) > TIME_RESYNC_SECONDS * 1000:
            helpers.sync_time(matrixportal.network, TIME_LOCATION)
            last_resync = ticks_ms()

        if helpers.is_night_time(NIGHT_START_HOUR, DAY_ROLLOVER_HOUR):
            if not is_dark:
                print("Entering power-saver mode until {:02d}:00.".format(DAY_ROLLOVER_HOUR))
                screen.clear()
                set_brightness(0.0)
                is_dark = True
            time.sleep(NIGHT_CHECK_INTERVAL_SECONDS)
            continue

        if is_dark:
            print("Waking up from power-saver mode.")
            set_brightness(1.0)
            is_dark = False

        today = helpers.effective_date(DAY_ROLLOVER_HOUR)
        if today != current_date:
            current_date = today
            current_pages = pages_for_date(today)

        screen.show_pages(current_pages, QUOTE_DISPLAY_SECONDS)
        screen.play_animation(ANIMATION_FRAMES, ANIMATION_FRAME_DELAY, ANIMATION_LOOPS)


main()