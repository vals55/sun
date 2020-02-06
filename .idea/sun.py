#!/usr/bin/python3
#(c) 2020, Valentin Shokurov
#Sun is a script to run something on daytime events.
#Class ported from suncalc https://github.com/mourner/suncalc

import math
import time
import datetime
import subprocess
from datetime import timedelta

class sun():

    pi = math.pi
    rad = math.pi / 180
    dayMs = 1000 * 60 * 60 * 24
    J0 = 0.0009
    J1970 = 2440588
    J2000 = 2451545
    e = rad * 23.4397

    def __init__(self, latitude, longitude, height):
        self.latitude = latitude
        self.longitude = longitude
        self.height = height

    def toJulian(date):
        return (time.mktime(date.timetuple()) * 1000) / sun.dayMs - 0.5 + sun.J1970

    def fromJulian(j):
        return datetime.datetime.fromtimestamp(((j + 0.5 - sun.J1970) * sun.dayMs) / 1000.0)

    def toDays(date):
        return sun.toJulian(date) - sun.J2000

    def rightAscension(l, b):
        return math.atan(math.sin(l) * math.cos(sun.e) - math.tan(b) * math.sin(sun.e), math.cos(l))

    def declination(l, b):
        return math.asin(math.sin(b) * math.cos(sun.e) + math.cos(b) * math.sin(sun.e) * math.sin(l))

    def azimuth(H, phi, dec):
        return math.atan(math.sin(H), math.cos(H) * math.sin(phi) - math.tan(dec) * math.cos(phi))

    def altitude(H, phi, dec):
        return math.asin(math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(H))

    def siderealTime(d, lw):
        return sun.rad * (280.16 + 360.9856235 * d) - lw

    def solarMeanAnomaly(d):
        return sun.rad * (357.5291 + 0.98560028 * d)

    def eclipticLongitude(M):
        C = sun.rad * (1.9148 * math.sin(M) + 0.02 * math.sin(2 * M) + 0.0003 * math.sin(3 * M))
        P = sun.rad * 102.9372
        return M + C + P + sun.pi

    def sunCoords(d):
        M = sun.solarMeanAnomaly(d)
        L = sun.eclipticLongitude(M)
        self.dec = sun.declination(L, 0)
        self.ra = sun.rightAscension(L, 0)

    def julianCycle(d, lw):
        return round(d - sun.J0 - lw / (2 * sun.pi))

    def approxTransit(Ht, lw, n):
        return sun.J0 + (Ht + lw) / (2 * sun.pi) + n

    def solarTransitJ(ds, M, L):
        return sun.J2000 + ds + 0.0053 * math.sin(M) - 0.0069 * math.sin(2 * L)

    def hourAngle(h, phi, d):
        return math.acos((math.sin(h) - math.sin(phi) * math.sin(d)) / (math.cos(phi) * math.cos(d)))

    def observerAngle(height):
        return -2.076 * math.sqrt(height) / 60

    def getSetJ(h, lw, phi, dec, n, M, L):
        w = sun.hourAngle(h, phi, dec)
        a = sun.approxTransit(w, lw, n)
        st = sun.solarTransitJ(a, M, L)
        return st

    def calculate(self, date):
        lw = sun.rad * -self.longitude
        phi = sun.rad * self.latitude

        dh = sun.observerAngle(self.height)

        d = sun.toDays(date)
        n = sun.julianCycle(d, lw)
        ds = sun.approxTransit(0, lw, n)

        M = sun.solarMeanAnomaly(ds)
        L = sun.eclipticLongitude(M)
        dec = sun.declination(L, 0)

        Jnoon = sun.solarTransitJ(ds, M, L)
        self.transit = sun.fromJulian(Jnoon)
        Jnadir = Jnoon - 0.5
        self.nadir = sun.fromJulian(Jnadir)

        # Angles for calculate events
        #  -0.833 sunrise / sunset according refraction (size of sun disk - 31'59")
        #  -0.3   sunrise end / sunset start
        #  -6     dawn / dusk
        # -12     nautical dawn / nautical dusk
        # -18     night end / night begin
        #   6     morning golden hour / evening golden hour

        h0 = (-0.833 + dh) * sun.rad
        Jset = sun.getSetJ(h0, lw, phi, dec, n, M, L)
        Jrise = Jnoon - (Jset - Jnoon)
        self.sunrise = sun.fromJulian(Jrise)
        self.sunset = sun.fromJulian(Jset)

        h0 = (-6.0 + dh) * sun.rad
        Jset = sun.getSetJ(h0, lw, phi, dec, n, M, L)
        Jrise = Jnoon - (Jset - Jnoon)
        self.dawn = sun.fromJulian(Jrise)
        self.dusk = sun.fromJulian(Jset)

        h0 = (6.0 + dh) * sun.rad
        Jset = sun.getSetJ(h0, lw, phi, dec, n, M, L)
        Jrise = Jnoon - (Jset - Jnoon)
        self.goldenstart = sun.fromJulian(Jrise)
        self.goldenend = sun.fromJulian(Jset)

logFileName = '/var/log/sun.log'
motion = '/etc/init.d/motion'
action = 'restart'

sunrise_done = False
transit_done = False
sunset_done = False
goldenstart_done = False
goldenend_done = False

def logNote(s):
    logFile = open(logFileName,'a')
    logFile.write('{} {}\n'.format(datetime.datetime.now().strftime('%b %d %H:%M:%S'), s))
    logFile.close()

def reset():
    sunrise_done = False
    transit_done = False
    sunset_done = False
    goldenstart_done = False
    goldenend_done = False

s = sun(55.8269706, 37.5247134, 180)
logNote('Calculations are for {:8.5f} N latitude and {:9.5f} E longitude'.format(s.latitude, s.longitude))
currentDateTime = datetime.datetime.now()
s.calculate(currentDateTime)
reset()

logNote('dawn        = {}'.format(s.dawn))
logNote('sunrise     = {}'.format(s.sunrise))
logNote('golden hour = {}'.format(s.goldenstart))
logNote('transit     = {}'.format(s.transit))
logNote('golden hour = {}'.format(s.goldenend))
logNote('sunset      = {}'.format(s.sunset))
logNote('dusk        = {}'.format(s.dusk))

while True:
    currentDateTime = datetime.datetime.now()
    s.calculate(currentDateTime)

    if currentDateTime > s.dusk:
        tomorrowDateTime = currentDateTime + timedelta(days = 1)
        s.calculate(tomorrowDateTime)
        reset()

    if currentDateTime > s.sunrise and not sunrise_done:
        sunrise_done = True
        logNote('Sunrise has come {}'.format(s.sunrise))
        p = subprocess.Popen([motion, action])

    if currentDateTime > s.goldenstart and not goldenstart_done:
        goldenstart_done = True
        logNote('Morning golden hour has come {}'.format(s.goldenstart))
        p = subprocess.Popen([motion, action])

    if currentDateTime > s.transit and not transit_done:
        transit_done = True
        logNote('Transit has come {}'.format(s.transit))
        p = subprocess.Popen([motion, action])

    if currentDateTime > s.goldenend and not goldenend_done:
        goldenend_done = True
        logNote('Evening golden hour has come {}'.format(s.goldenend))
        p = subprocess.Popen([motion, action])

    if currentDateTime > s.sunset and not sunset_done:
        sunset_done = True
        logNote('Sunset has come {}'.format(s.sunset))
        p = subprocess.Popen([motion, action])

    time.sleep(600)

