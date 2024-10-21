# SPDX-FileCopyrightText: 2024 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT
# pylint: disable=redefined-outer-name, eval-used, wrong-import-order, unsubscriptable-object

import time
import board
import terminalio
import displayio
import adafruit_imageload
import microcontroller
from adafruit_display_text import label
from adafruit_magtag.magtag import MagTag
import adafruit_bme680
from adafruit_bitmap_font import bitmap_font
from adafruit_ticks import ticks_ms, ticks_add, ticks_diff

# --| USER CONFIG |--------------------------
LAT = 50  # latitude
LON = -50  # longitude
TMZ = "America/New_York"  # https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
METRIC = False  # set to True for metric units
CITY = "CITY NAME"  # optional
# -------------------------------------------

i2c = board.STEMMA_I2C()
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c, debug=False)

# ----------------------------
# Define various assets
# ----------------------------
BACKGROUND_BMP = "/bmps/weather_bg.bmp"
ICONS_LARGE_FILE = "/bmps/weather_icons_70px.bmp"
ICONS_SMALL_FILE = "/bmps/weather_icons_20px.bmp"
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

# Weather Code Information from https://open-meteo.com/en/docs
# Code 	Description
# 0 	Clear sky
# 1, 2, 3 	Mainly clear, partly cloudy, and overcast
# 45, 48 	Fog and depositing rime fog
# 51, 53, 55 	Drizzle: Light, moderate, and dense intensity
# 56, 57 	Freezing Drizzle: Light and dense intensity
# 61, 63, 65 	Rain: Slight, moderate and heavy intensity
# 66, 67 	Freezing Rain: Light and heavy intensity
# 71, 73, 75 	Snow fall: Slight, moderate, and heavy intensity
# 77 	Snow grains
# 80, 81, 82 	Rain showers: Slight, moderate, and violent
# 85, 86 	Snow showers slight and heavy
# 95 * 	Thunderstorm: Slight or moderate
# 96, 99 * 	Thunderstorm with slight and heavy hail

# Map the above WMO codes to index of icon in 3x3 spritesheet
WMO_CODE_TO_ICON = (
    (0,),  # 0 = sunny
    (1,),  # 1 = partly sunny/cloudy
    (2,),  # 2 = cloudy
    (3,),  # 3 = very cloudy
    (61, 63, 65),  # 4 = rain
    (51, 53, 55, 80, 81, 82),  # 5 = showers
    (95, 96, 99),  # 6 = storms
    (56, 57, 66, 67, 71, 73, 75, 77, 85, 86),  # 7 = snow
    (45, 48),  # 8 = fog and stuff
)

magtag = MagTag()

# ----------------------------
# Backgrounnd bitmap
# ----------------------------
magtag.graphics.set_background(BACKGROUND_BMP)

# ----------------------------
# Weather icons sprite sheet
# ----------------------------
icons_large_bmp, icons_large_pal = adafruit_imageload.load(ICONS_LARGE_FILE)
icons_small_bmp, icons_small_pal = adafruit_imageload.load(ICONS_SMALL_FILE)

# /////////////////////////////////////////////////////////////////////////
#  helper functions


def get_forecast():
    URL = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&"
    URL += "daily=temperature_2m_max,temperature_2m_min"
    URL += ",sunrise,sunset,weather_code"
    URL += "&hourly=dew_point_2m"
    URL += "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m"
    URL += "&timeformat=unixtime"
    URL += f"&timezone={TMZ}"
    resp = magtag.network.fetch(URL)
    return resp


def make_banner(x=0, y=0):
    """Make a single future forecast info banner group."""
    day_of_week = label.Label(terminalio.FONT, text="DAY", color=0x000000)
    day_of_week.anchor_point = (0, 0.5)
    day_of_week.anchored_position = (0, 10)

    icon = displayio.TileGrid(
        icons_small_bmp,
        pixel_shader=icons_small_pal,
        x=25,
        y=0,
        width=1,
        height=1,
        tile_width=20,
        tile_height=20,
    )

    day_temp = label.Label(terminalio.FONT, text="+100F", color=0x000000)
    day_temp.anchor_point = (0, 0.5)
    day_temp.anchored_position = (50, 10)

    group = displayio.Group(x=x, y=y)
    group.append(day_of_week)
    group.append(icon)
    group.append(day_temp)

    return group


def temperature_text(tempC):
    if METRIC:
        return "{:3.0f}C".format(tempC)
    else:
        return "{:3.0f}F".format(32.0 + 1.8 * tempC)


def wind_text(speedkmh, direction):
    wind_dir = "N"
    if direction < 337:
        wind_dir = "NW"
    if direction < 293:
        wind_dir = "W"
    if direction < 247:
        wind_dir = "SW"
    if direction < 202:
        wind_dir = "S"
    if direction < 157:
        wind_dir = "SE"
    if direction < 112:
        wind_dir = "E"
    if direction < 67:
        wind_dir = "NE"
    if direction < 22:
        wind_dir = "N"

    wtext = f"from {wind_dir} "

    if METRIC:
        wtext += "{:2.0f}kmh".format(speedkmh)
    else:
        wtext += "{:2.0f}mph".format(0.621371 * speedkmh)
    return wtext


def update_today(data):
    """Update today weather info."""
    # date text
    print(data)
    s = data["current"]["time"] + data["utc_offset_seconds"]
    t = time.localtime(s)
    today_date.text = "{} {} {}, {}".format(
        DAYS[t.tm_wday].upper(), MONTHS[t.tm_mon - 1].upper(), t.tm_mday, t.tm_year
    )
    # weather icon
    w = data["current"]["weather_code"]
    today_icon[0] = next(i for i, t in enumerate(WMO_CODE_TO_ICON) if w in t)
    # temperatures
    today_low_temp.text = temperature_text(data["daily"]["temperature_2m_min"][0])
    today_high_temp.text = temperature_text(data["daily"]["temperature_2m_max"][0])
    now_temp.text = temperature_text(data["current"]["temperature_2m"])
    dew.text = temperature_text(data['hourly']['dew_point_2m'][t.tm_hour])
    feels_temp.text = temperature_text(data["current"]["apparent_temperature"])
    # wind
    s = data["current"]["wind_speed_10m"]
    d = data["current"]["wind_direction_10m"]
    today_wind.text = wind_text(s, d)
    # sunrise/set
    sr = time.localtime(data["daily"]["sunrise"][0] + data["utc_offset_seconds"])
    ss = time.localtime(data["daily"]["sunset"][0] + data["utc_offset_seconds"])
    today_sunrise.text = "{:2d}:{:02d} AM".format(sr.tm_hour, sr.tm_min)
    today_sunset.text = "{:2d}:{:02d} PM".format(ss.tm_hour - 12, ss.tm_min)


def update_future(data):
    """Update the future forecast info."""
    for i, banner in enumerate(future_banners):
        # day of week
        s = data["daily"]["time"][i + 1] + data["utc_offset_seconds"]
        t = time.localtime(s)
        banner[0].text = DAYS[t.tm_wday][:3].upper()
        # weather icon
        w = data["daily"]["weather_code"][i + 1]
        banner[1][0] = next(x for x, t in enumerate(WMO_CODE_TO_ICON) if w in t)
        # temperature
        t = data["daily"]["temperature_2m_max"][i + 1]
        banner[2].text = temperature_text(t)


# ===========
# U I
# ===========
today_date = label.Label(terminalio.FONT, text="?" * 30, color=0x000000)
today_date.anchor_point = (0, 0)
today_date.anchored_position = (15, 14)

location_name = label.Label(terminalio.FONT, color=0x000000)
if CITY:
    location_name.text = f"{CITY[:16]}"
else:
    location_name.text = f"({LAT},{LON})"

location_name.anchor_point = (0, 0)
location_name.anchored_position = (15, 25)

today_icon = displayio.TileGrid(
    icons_large_bmp,
    pixel_shader=icons_small_pal,
    x=10,
    y=35,
    width=1,
    height=1,
    tile_width=70,
    tile_height=70,
)

today_low_temp = label.Label(terminalio.FONT, text="+100F", color=0x000000)
today_low_temp.anchor_point = (0.5, 0)
today_low_temp.anchored_position = (123, 52)

today_high_temp = label.Label(terminalio.FONT, text="+100F", color=0x000000)
today_high_temp.anchor_point = (0.5, 0)
today_high_temp.anchored_position = (148, 52)

now_temp = label.Label(terminalio.FONT, text="+100F", color=0x000000)
now_temp.anchor_point = (0.5, 0)
now_temp.anchored_position = (175, 52)

dew = label.Label(terminalio.FONT, text="+100F", color=0x000000)
dew.anchor_point = (0.5, 0)
dew.anchored_position = (126, 72)

feels_temp = label.Label(terminalio.FONT, text="+100F", color=0x000000)
feels_temp.anchor_point = (0.5, 0)
feels_temp.anchored_position = (182, 72)

today_wind = label.Label(terminalio.FONT, text="99m/s", color=0x000000)
today_wind.anchor_point = (0, 0.5)
today_wind.anchored_position = (110, 95)

today_sunrise = label.Label(terminalio.FONT, text="12:12 PM", color=0x000000)
today_sunrise.anchor_point = (0, 0.5)
today_sunrise.anchored_position = (45, 117)

today_sunset = label.Label(terminalio.FONT, text="12:12 PM", color=0x000000)
today_sunset.anchor_point = (0, 0.5)
today_sunset.anchored_position = (130, 117)

today_banner = displayio.Group()
today_banner.append(today_date)
today_banner.append(location_name)
today_banner.append(today_icon)
today_banner.append(today_low_temp)
today_banner.append(today_high_temp)
today_banner.append(now_temp)
today_banner.append(dew)
today_banner.append(feels_temp)
today_banner.append(today_wind)
today_banner.append(today_sunrise)
today_banner.append(today_sunset)

future_banners = [
    make_banner(x=210, y=18),
    make_banner(x=210, y=39),
    make_banner(x=210, y=60),
    make_banner(x=210, y=81),
    make_banner(x=210, y=102),
]

magtag.splash.append(today_banner)
for future_banner in future_banners:
    magtag.splash.append(future_banner)

sensor_banner = displayio.Group()

big_font_file = "/OCRA_big.pcf"
big_font = bitmap_font.load_font(big_font_file)

SENSOR_BMP = "/bmps/magtag_sensor_bg.bmp"
sensor_temp = label.Label(big_font, text="+100F", color=0x000000, x=65, y=35)

sensor_humid = label.Label(big_font, text="+100F", color=0x000000, x = 65, y = 94)
sensor_banner.append(sensor_temp)
sensor_banner.append(sensor_humid)

weather_time = (15 * 60) * 1000
weather_clock = ticks_ms()
sensor_time = 5 * 1000
sensor_clock = ticks_ms()
update_count = 0
first_run = True
show_sensor = False
while True:
    try:
        if magtag.peripherals.button_a_pressed or magtag.peripherals.button_b_pressed or magtag.peripherals.button_c_pressed or magtag.peripherals.button_d_pressed:
            show_sensor = not show_sensor
            if show_sensor:
                magtag.graphics.set_background(SENSOR_BMP)

                for future_banner in future_banners:
                    magtag.splash.remove(future_banner)
                magtag.splash.remove(today_banner)
                magtag.splash.append(sensor_banner)
            else:
                magtag.graphics.set_background(BACKGROUND_BMP)
                magtag.splash.remove(sensor_banner)
                magtag.splash.append(today_banner)
                for future_banner in future_banners:
                    magtag.splash.append(future_banner)
            time.sleep(magtag.display.time_to_refresh + 1)
            magtag.display.refresh()
            time.sleep(magtag.display.time_to_refresh + 1)

        if ticks_diff(ticks_ms(), weather_clock) >= weather_time or first_run:
            print("Fetching forecast...")
            resp_data = get_forecast()
            forecast_data = resp_data.json()

            print("Updating...")
            update_today(forecast_data)
            update_future(forecast_data)

            print("Refreshing...")
            time.sleep(magtag.display.time_to_refresh + 1)
            magtag.display.refresh()
            time.sleep(magtag.display.time_to_refresh + 1)
            first_run = False
            weather_clock = ticks_add(weather_clock, weather_time)
        if ticks_diff(ticks_ms(), sensor_clock) >= sensor_time:
            converted_temp = 32.0 + 1.8 * (bme680.temperature - 2)
            print(f"\nTemperature: {converted_temp}")
            sensor_temp.text = f"{converted_temp:.1f}°F"
            print("Humidity: %0.1f %%" % bme680.relative_humidity)
            sensor_humid.text = f"{bme680.relative_humidity:.1f}%"
            if show_sensor:
                update_count += 1
                if update_count > 60:
                    update_count = 0
                    time.sleep(magtag.display.time_to_refresh + 1)
                    magtag.display.refresh()
                    time.sleep(magtag.display.time_to_refresh + 1)
            sensor_clock = ticks_add(sensor_clock, sensor_time)
    except Exception as error:
        print(f"error: {error}!")
        time.sleep(2)
        #microcontroller.reset()
