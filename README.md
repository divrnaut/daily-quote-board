# Daily Quote Board — MatrixPortal M4

Hello, [FRIEND]! It's dangerous. Take this with you.

It is an Adafruit 64x32 RGB Matrix + MatrixPortal M4. This little board is meant
to be a daily dose of inspiration, a splash of color, and a personal favorite
tucked into your space. Every day at 6:00 AM it picks a new quote from a local
file and a fresh pair of quote/source colors from a palette file, then scrolls
it across the screen with a little motion and personality. I hope it brightens
your office and keeps a little encouragement in view!

## ✨ Quick start

- Add your own quotes in `quotes.json`
- Swap the colors in `colors.json`
- Edit `settings.toml` with your WiFi name and password
- Keep the board connected to the Internet so it can fetch the correct local time each day
- Power it on and let it do its thing

## 📁 What’s in this folder

```
code.py                  - the program that runs on the board
quotes.json              - the list of quotes (edit this to customize!)
colors.json              - the color palette to pick from each day
settings.toml            - for your WiFi / Adafruit IO credentials
frames/
  frame1.bmp             
  frame2.bmp               
  frame3.bmp
```

## 🛠️ Hardware / software

- Adafruit MatrixPortal M4
- The 64x32 RGB LED matrix panel, connected per Adafruit's guide
- A USB-C to USB-A cable
- Housing: Overture Starry Blue PETG, Rust-oleum Glossy finish
- CircuitPython installed on the board (this was written against CircuitPython 9.x)
- A free [Adafruit IO](https://io.adafruit.com) account — only used to fetch
  the correct time once a day; nothing else on your board touches it

## ✅ Setup for a working board

1. **Set up your credentials.** Edit `settings.toml` to match your home WiFi:

   ```toml
   WIFI_SSID = "Your WiFi Network Name"
   WIFI_PASSWORD = "Your WiFi Password"
   ADAFRUIT_IO_USERNAME = "your-adafruit-io-username"
   ADAFRUIT_IO_KEY = "your-adafruit-io-key"
   ```

   The WiFi details are required so the board can connect to your network.
   The Adafruit IO credentials are used to fetch the current local time once
   a day. This is important because the board decides which quote to show
   based on the date and time, and it only rotates at the right time when it
   knows the correct local time. Copy the finished `settings.toml` file to
   the root of the `CIRCUITPY` drive (next to `code.py`).

   ### Creating an Adafruit account and finding your IO Key

   If you do not already have an Adafruit account, create one at
   [adafruit.com](https://www.adafruit.com/) and sign in.

   Then go to [Adafruit IO](https://io.adafruit.com/) and log in. Once you are
   signed in, open your profile or account settings and look for the page that
   shows your Adafruit IO username and the key for your account. That key is the
   value you paste into `ADAFRUIT_IO_KEY` in `settings.toml`.

   The username and key are both required for the board to fetch the time. If you
   are unsure where to find them, open the Adafruit IO dashboard and look for
   your username at the top of the page and the "AIO Key" or "Active Key"
   section in your account settings.

2. **Power it up.** The board will connect to WiFi, fetch the time, pick
   today's quote, and start scrolling.

## 🔄 If the board was reset or the firmware was reinstalled

If the board has been reset, reformatted, or the CircuitPython firmware was
reinstalled, use these steps before the normal setup above.

1. **Install CircuitPython** on the MatrixPortal M4 if you haven't already
   (Adafruit's [CircuitPython Setup guide](https://learn.adafruit.com/adafruit-matrixportal-m4/circuitpython-setup)
   walks through this).

2. **Install the required libraries.** The easiest way is with
   [`circup`](https://learn.adafruit.com/keep-your-circuitpython-libraries-on-devices-up-to-date-with-circup):

   ```
   circup install adafruit_matrixportal adafruit_display_text adafruit_bitmap_font
   ```

   `circup` will automatically pull in the lower-level dependencies
   (`adafruit_esp32spi`, `adafruit_requests`, `adafruit_portalbase`,
   `adafruit_bus_device`, `neopixel`, `adafruit_debouncer`, etc.). If you'd
   rather do it by hand, grab those from the
   [Adafruit CircuitPython Library Bundle](https://circuitpython.org/libraries)
   and drop them in `CIRCUITPY/lib/`.

3. **Copy the project files** onto `CIRCUITPY`:
   - `code.py` → root of CIRCUITPY
   - `quotes.json` → root of CIRCUITPY
   - `colors.json` → root of CIRCUITPY
   - `frames/` folder (with its 3 `.bmp` files) → root of CIRCUITPY

4. Then return to the setup steps above and fill in your WiFi and Adafruit IO
   credentials.

## 💬 Customizing the quotes

This is the easiest part to personalize. Open `quotes.json` and replace, add, delete any. It's a JSON array of quote objects,
each with a `text` field and optional `author` / `source` fields:

```json
[
  {"text": "You've got this, soldier.", "author": "Karlach", "source": "BG3"},
  {"text": "sometimes it be like it do.", "author": "Taniya"}
]
```

- `text` is required.
- `author` and `source` are both optional — include whichever you have.
  If both are present they're shown together as `~Author, Source`; if
  only one is present, just that one is shown; if neither is present,
  the quote is shown on its own with no attribution line.
- Keep quotes on the shorter side (under ~90 characters including
  attribution) so they read comfortably on a 64x32 display — see the
  note below if you want to fit more text per quote.
- No code changes are needed — just edit the file and save it back to
  the board.

A couple of JSON-specific gotchas to watch for, since a syntax mistake
here will stop the whole program from starting:
- Every `text`/`author`/`source` value needs double quotes around it
  (not single quotes).
- Don't leave a trailing comma after the last item in the array.
- If a quote itself contains a double-quote character, escape it as
  `\"` (e.g. `"text": "She said \"go for it\"."`).
- Unlike the old text-file format, JSON doesn't support `#` comment
  lines — if you want to jot notes to yourself, keep them in a
  separate file.
- If you're unsure your edits are valid JSON, paste the file into a
  free validator like [jsonlint.com](https://jsonlint.com) before
  copying it onto the board.

The board picks which quote to show using the date itself (not randomly),
so:
- the quote only changes once a day, right at 6:00 AM local time
- if the board loses power and reboots mid-day, it'll show the *same*
  quote it was already on, instead of picking a new one
- the sequence looks shuffled day to day rather than counting predictably
  through the list - though unlike a strict rotation, that means a quote
  can occasionally repeat sooner than a full pass through the list, by
  design (see the comment on `quote_index_for_date` in `code.py` if you
  want the details)

## 🎨 Customizing the colors

Open `colors.json` — it's a JSON array of named colors:

```json
[
  {"color": "forest_green", "value": "#3C4A20"},
  {"color": "sky_blue", "value": "#3AA0FF"}
]
```

- `color` is just a label (used in the serial console's log output so you
  can see which colors got picked) - it doesn't need to be unique or
  follow any particular format.
- `value` is the color itself, as a hex string like `"#3C4A20"` (the
  `#` is the recommended format; older `"0x3C4A20"` values still work too).
- Add as many colors as you like - a bigger palette means more variety
  day to day.

**Each day, alongside the day's quote, one color from this list is picked
for the quote text and a different one for the author/source line - using
the same date-based approach as the quote itself, so the pair only changes
once a day and survives reboots.** If you have more than one color in the
list, the quote and source colors are guaranteed not to land on the exact
same color on the same day.

If `colors.json` is missing or can't be read, the board falls back to a
fixed white quote / amber source (the same colors used before this file
existed) rather than failing to start.

## 🔧 Tuning the timing and look

All the knobs you'd want to turn live at the top of `code.py`:

| Setting | What it controls |
|---|---|
| `DAY_ROLLOVER_HOUR` | What hour (24h, local time) a new quote is picked |
| `QUOTE_DISPLAY_SECONDS` | Total time budget (default: 2 minutes) for cycling through a quote's pages before moving to the animation |
| `PAGE_HOLD_SECONDS` | How long each page of quote text is held before toggling to the next one |
| `ATTRIBUTION_HOLD_SECONDS` | How long the author/source page is held - shorter than `PAGE_HOLD_SECONDS`, since it's meant to be a quick beat |
| `LETTER_SLIDE_STAGGER` | Delay before each successive letter starts sliding (controls how fast words assemble) |
| `LETTER_SLIDE_DURATION` | How long one letter takes to land, once it starts |
| `LETTER_SLIDE_START_OFFSET` | Pixels to the right of its landing spot a letter starts sliding from |
| `LETTER_SLIDE_FRAME_DELAY` | Time between animation redraws - lower is smoother but uses more CPU |
| `ANIMATION_FRAME_DELAY` | How long each of the 3 loading frames is shown |
| `ANIMATION_LOOPS` | How many times the 3-frame animation loops before returning to the quote |
| `QUOTE_COLOR` / `SOURCE_COLOR` | Text colors, as hex (e.g. `#FFFFFF` for white) |
| `TIME_LOCATION` | IANA timezone name used for local time / DST |
| `PADDING_LEFT/RIGHT/TOP/BOTTOM` | Pixels hidden by your case on each side (see above) |


### ❤️, [YOUR BEST FRIEND]
