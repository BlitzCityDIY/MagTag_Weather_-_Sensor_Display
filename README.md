# MagTag Weather & Sensor Display
Coded using CircuitPython and adapted from the [MagTag Daily Weather project](https://learn.adafruit.com/magtag-weather)

Weather API is OpenMeteo. Sensor is BME680, but any sensor can be subbed in. The four buttons toggle between showing the current weather or the data from the sensor. When showing the weather, the API is polled and the display is updated every 15 minutes. When showing the sensor, the sensor is polled every 5 seconds but the display updates every 5 minutes.
