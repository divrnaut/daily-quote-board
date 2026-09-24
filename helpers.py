# Support code for the Daily Quote Board: file loading, time and daily
# picks, pagination, and drawing. Settings are passed in from code.py.

import gc
import json
import time

import displayio

from adafruit_display_text import wrap_text_to_pixels
from adafruit_display_text.label import Label
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff, ticks_less

# Timing uses integer ms ticks instead of time.monotonic(): monotonic() is a
# float and loses precision as uptime grows (~31ms steps after a day), which
# makes the letter animation stutter. Ticks stay exact but can only measure
# gaps up to ~3 days.


# --- Quotes and colors ---

def load_quotes(path):
    """
    Load quotes.json as a list of (text, author, source) tuples.

    Format: [{"text": "You've got this, soldier.", "author": "Karlach", "source": "BG3"}]
    author and source are optional.
    """
    with open(path, "r") as f:
        data = json.load(f)

    quotes = []
    for entry in data:
        text = (entry.get("text") or "").strip()
        if not text:
            continue
        author = (entry.get("author") or "").strip()
        source = (entry.get("source") or "").strip()
        quotes.append((text, author, source))

    if not quotes:
        raise RuntimeError("No quotes found in " + path)
    return quotes


def format_attribution(author, source):
    """Join author and source, e.g. 'Karlach, BG3'."""
    if author and source:
        return "{}, {}".format(author, source)
    return author or source


def load_colors(path):
    """
    Load colors.json as a list of (name, color_int) tuples.

    Format: [{"color": "forest_green", "value": "#3C4A20"}]
    value may be a hex string (with or without "#"/"0x") or an integer.
    """
    with open(path, "r") as f:
        data = json.load(f)

    colors = []
    for entry in data:
        name = (entry.get("color") or "").strip()
        raw_value = entry.get("value")
        if not name or raw_value is None:
            continue
        try:
            if isinstance(raw_value, str):
                text = raw_value.strip().lstrip("#")
                if text.lower().startswith("0x"):
                    text = text[2:]
                value = int(text, 16)
            else:
                value = int(raw_value)
        except ValueError:
            print("Skipping color '{}' - couldn't parse value {!r}".format(name, raw_value))
            continue
        colors.append((name, value))

    if not colors:
        raise RuntimeError("No colors found in " + path)
    return colors


# --- Time and daily picks ---

def sync_time(network, location):
    """Set the RTC from network time, retrying a few times."""
    for _ in range(3):
        try:
            gc.collect()  # HTTPS needs the memory
            network.get_local_time(location=location)
            print("Time synced:", time.localtime())
            return True
        except Exception as e:
            print("Time sync failed ({}), retrying...".format(e))
            time.sleep(5)
    print("Could not sync time, will keep running on the last known time.")
    return False


def effective_date(rollover_hour, now=None):
    """(year, month, day) for today, where the day starts at rollover_hour."""
    now = now or time.localtime()
    if now.tm_hour < rollover_hour:
        yesterday_epoch = time.mktime(now) - 86400
        now = time.localtime(yesterday_epoch)
    return (now.tm_year, now.tm_mon, now.tm_mday)


def is_night_time(night_start_hour, rollover_hour, now=None):
    """True between night_start_hour and rollover_hour the next morning."""
    now = now or time.localtime()
    return now.tm_hour >= night_start_hour or now.tm_hour < rollover_hour


def _mix(x):
    """32-bit integer hash so consecutive days map to unrelated values."""
    x &= 0xFFFFFFFF
    x = ((x ^ (x >> 16)) * 0x45D9F3B) & 0xFFFFFFFF
    x = ((x ^ (x >> 16)) * 0x45D9F3B) & 0xFFFFFFFF
    x = x ^ (x >> 16)
    return x


def _day_number(date_tuple):
    """Days since the epoch for a (year, month, day) tuple."""
    year, month, day = date_tuple
    day_struct = (year, month, day, 12, 0, 0, 0, -1, -1)
    return int(time.mktime(day_struct) // 86400)


def quote_index_for_date(date_tuple, count):
    """
    Quote index for a date. Stable across reboots with no saved state, and
    shuffled rather than sequential. Repeats are possible before every quote
    has been shown.
    """
    return _mix(_day_number(date_tuple)) % count


def colors_for_date(date_tuple, count):
    """
    (quote_color_index, source_color_index) for a date. Each uses its own
    salt so they vary independently, and they never match when count > 1.
    """
    day_number = _day_number(date_tuple)
    quote_idx = _mix(day_number ^ 0x9E3779B1) % count
    source_idx = _mix(day_number ^ 0x85EBCA6B) % count
    if count > 1 and source_idx == quote_idx:
        source_idx = (source_idx + 1) % count
    return quote_idx, source_idx


# --- Pagination ---

def paginate_quote(
    quote_text,
    attribution_text,
    quote_color,
    source_color,
    *,
    font,
    max_width,
    max_lines,
    page_hold_seconds,
    attribution_hold_seconds,
):
    """
    Wrap the quote and attribution into pages of (lines, color, hold_seconds).
    Quote pages come first, followed by attribution pages if there is one.
    """
    pages = []

    quote_lines = wrap_text_to_pixels(quote_text, max_width, font)
    for i in range(0, len(quote_lines), max_lines):
        pages.append((quote_lines[i : i + max_lines], quote_color, page_hold_seconds))

    if attribution_text:
        attribution_lines = wrap_text_to_pixels("~" + attribution_text, max_width, font)
        for i in range(0, len(attribution_lines), max_lines):
            pages.append(
                (attribution_lines[i : i + max_lines], source_color, attribution_hold_seconds)
            )

    return pages


# --- Drawing ---

class QuoteScreen:
    """Draws quote pages, the loading animation, and blank screens."""

    def __init__(
        self,
        display,
        root_group,
        *,
        font,
        line_height,
        visible_height,
        slide_start_offset,
        slide_stagger,
        slide_duration,
        slide_frame_delay,
    ):
        self.display = display
        self.root_group = root_group
        self.font = font
        self.line_height = line_height
        self.visible_height = visible_height
        self.slide_start_offset = slide_start_offset
        self.slide_frame_delay = slide_frame_delay
        self.stagger_ms = int(slide_stagger * 1000)
        self.duration_ms = max(1, int(slide_duration * 1000))

    def clear(self):
        while len(self.root_group) > 0:
            self.root_group.pop()
        gc.collect()

    def reveal_page(self, lines, color):
        """
        Slide each letter in from the right, one after another in reading
        order. Assumes a monospace font. Leaves the finished page on screen
        and returns its group.
        """
        line_height = self.line_height
        offset = self.slide_start_offset
        duration_ms = self.duration_ms
        duration_sq = duration_ms * duration_ms

        total_height = len(lines) * line_height
        start_y = max(0, (self.visible_height - total_height) // 2) + line_height // 2
        char_width = self.font.get_bounding_box()[0]

        page_group = displayio.Group()
        self.clear()
        self.root_group.append(page_group)

        letters = []  # (label, rest_x, start_ms)
        next_start_ms = 0
        for line_index, line in enumerate(lines):
            target_y = start_y + line_index * line_height
            for char_index, ch in enumerate(line):
                if ch.strip():
                    label = Label(self.font, text=ch, color=color)
                    label.anchor_point = (0.0, 0.5)
                    label.anchored_position = (char_index * char_width, target_y)
                    # Animate .x directly; cheaper than anchored_position.
                    rest_x = label.x
                    label.x = rest_x + offset
                    page_group.append(label)
                    letters.append((label, rest_x, next_start_ms))
                next_start_ms += self.stagger_ms  # spaces still get a beat

        # Letters in motion form a contiguous window, so only that window is
        # updated each frame. Integer math keeps the loop allocation-free.
        count = len(letters)
        first_active = 0
        try:
            self.display.auto_refresh = False
            animation_start = ticks_ms()
            while first_active < count:
                elapsed = ticks_diff(ticks_ms(), animation_start)
                i = first_active
                while i < count:
                    label, rest_x, letter_start = letters[i]
                    remaining = duration_ms - (elapsed - letter_start)
                    if remaining >= duration_ms:
                        break  # not started yet
                    if remaining <= 0:
                        label.x = rest_x
                        first_active = i + 1
                    else:
                        # quadratic ease-out
                        label.x = rest_x + offset * remaining * remaining // duration_sq
                    i += 1
                self.display.refresh()
                time.sleep(self.slide_frame_delay)
        finally:
            self.display.auto_refresh = True

        return page_group

    def show_pages(self, pages, total_seconds):
        """
        Cycle through pages for about total_seconds. A new pass only starts
        if the previous one would still fit, so this ends early rather than
        late. The first pass always runs in full.
        """
        if not pages:
            return
        deadline = ticks_add(ticks_ms(), int(total_seconds * 1000))
        while True:
            pass_start = ticks_ms()
            for lines, color, hold_seconds in pages:
                self.reveal_page(lines, color)
                time.sleep(hold_seconds)
            pass_ms = ticks_diff(ticks_ms(), pass_start)
            if ticks_diff(deadline, ticks_ms()) < pass_ms:
                break

    def play_animation(self, frame_paths, frame_delay, loops):
        """Play the loading frames, loading one BMP at a time to save memory."""
        self.clear()
        for _ in range(loops):
            for path in frame_paths:
                bitmap = displayio.OnDiskBitmap(path)
                tile_grid = displayio.TileGrid(bitmap, pixel_shader=bitmap.pixel_shader)
                frame_group = displayio.Group()
                frame_group.append(tile_grid)

                self.clear()
                self.root_group.append(frame_group)
                time.sleep(frame_delay)

        self.clear()
