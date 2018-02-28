import numpy as num

from pyrocko import util
from pyrocko.guts import Object, String, Timestamp, Float, Int, Unicode
from pyrocko.guts_array import Array
from pyrocko.squirrel import io


def str_or_none(x):
    if x is None:
        return None
    else:
        return str(x)


def float_or_none(x):
    if x is None:
        return None
    else:
        return float(x)


def int_or_none(x):
    if x is None:
        return None
    else:
        return int(x)


def tsplit(t):
    if t is None:
        return None, 0.0

    seconds = num.floor(t)
    offset = t - seconds
    return int(seconds), float(offset)


def tjoin(seconds, offset, deltat):
    if seconds is None:
        return None

    if deltat is not None and deltat < 1e-3:
        return util.hpfloat(seconds) + util.hpfloat(offset)
    else:
        return seconds + offset


tscale_min = 1
tscale_max = 365 * 24 * 3600  # last edge is one above
tscale_logbase = 20

tscale_edges = [tscale_min]
while True:
    tscale_edges.append(tscale_edges[-1]*tscale_logbase)
    if tscale_edges[-1] >= tscale_max:
        break


tscale_edges = num.array(tscale_edges)


def tscale_to_kscale(tscale):

    # 0 <= x < tscale_edges[1]: 0
    # tscale_edges[1] <= x < tscale_edges[2]: 1
    # ...
    # tscale_edges[len(tscale_edges)-1] <= x: len(tscale_edges)

    return int(num.searchsorted(tscale_edges, tscale))


class Content(Object):
    pass


class Waveform(Content):
    agency = String.T(default='FDSN', optional=True, help='Agency code (2-5)')
    network = String.T(help='Deployment/network code (1-8)')
    station = String.T(help='Station code (1-5)')
    location = String.T(optional=True, help='Location code (0-2)')
    channel = String.T(optional=True, help='Channel code (3)')
    extra = String.T(optional=True, help='Extra/custom code')

    tmin = Timestamp.T()
    tmax = Timestamp.T()

    deltat = Float.T(optional=True)

    data = Array.T(
        shape=(None,),
        dtype=num.float32,
        serialize_as='base64',
        serialize_dtype=num.dtype('<f4'),
        help='numpy array with data samples')


class Station(Content):
    agency = String.T(default='FDSN', optional=True, help='Agency code (2-5)')
    network = String.T(help='Deployment/network code (1-8)')
    station = String.T(help='Station code (1-5)')
    location = String.T(optional=True, help='Location code (0-2)')

    tmin = Timestamp.T(optional=True)
    tmax = Timestamp.T(optional=True)

    lat = Float.T()
    lon = Float.T()
    elevation = Float.T(optional=True)
    depth = Float.T(optional=True)

    description = Unicode.T(optional=True)


class Channel(Content):
    agency = String.T(default='FDSN', optional=True, help='Agency code (2-5)')
    network = String.T(help='Deployment/network code (1-8)')
    station = String.T(help='Station code (1-5)')
    location = String.T(optional=True, help='Location code (0-2)')
    channel = String.T(optional=True, help='Channel code (3)')

    tmin = Timestamp.T(optional=True)
    tmax = Timestamp.T(optional=True)

    lat = Float.T()
    lon = Float.T()
    elevation = Float.T(optional=True)
    depth = Float.T(optional=True)

    dip = Float.T(optional=True)
    azimuth = Float.T(optional=True)
    deltat = Float.T(optional=True)


class Response(Content):
    pass


class Event(Content):
    name = String.T(optional=True)
    time = Timestamp.T()
    duration = Float.T(optional=True)

    lat = Float.T()
    lon = Float.T()
    elevation = Float.T(optional=True)
    depth = Float.T(optional=True)

    magnitude = Float.T(optional=True)


class Nut(Object):
    file_path = String.T(optional=True)
    file_format = String.T(optional=True)
    file_mtime = Timestamp.T(optional=True)
    file_size = Int.T(optional=True)

    file_segment = Int.T(optional=True)
    file_element = Int.T(optional=True)

    kind = String.T()
    codes = String.T()

    tmin_seconds = Timestamp.T(optional=True)
    tmin_offset = Float.T(default=0.0, optional=True)
    tmax_seconds = Timestamp.T(optional=True)
    tmax_offset = Float.T(default=0.0, optional=True)

    deltat = Float.T(optional=True)

    content = Content.T(optional=True)

    content_in_db = False

    def __init__(
            self,
            file_path=None,
            file_format=None,
            file_mtime=None,
            file_size=None,
            file_segment=None,
            file_element=None,
            kind='',
            codes='',
            tmin_seconds=None,
            tmin_offset=0.0,
            tmax_seconds=None,
            tmax_offset=0.0,
            deltat=None,
            content=None,
            tmin=None,
            tmax=None,
            values_nocheck=None):

        if values_nocheck is not None:
            (self.file_path, self.file_format, self.file_mtime, self.file_size,
             self.file_segment, self.file_element,
             self.kind, self.codes,
             self.tmin_seconds, self.tmin_offset,
             self.tmax_seconds, self.tmax_offset,
             self.deltat) = values_nocheck

            self.content = None
        else:
            if tmin is not None:
                tmin_seconds, tmin_offset = tsplit(tmin)

            if tmax is not None:
                tmax_seconds, tmax_offset = tsplit(tmax)

            self.kind = str(kind)
            self.codes = str(codes)
            self.tmin_seconds = int_or_none(tmin_seconds)
            self.tmin_offset = float(tmin_offset)
            self.tmax_seconds = int_or_none(tmax_seconds)
            self.tmax_offset = float(tmax_offset)
            self.deltat = float_or_none(deltat)
            self.file_path = str_or_none(file_path)
            self.file_segment = int_or_none(file_segment)
            self.file_element = int_or_none(file_element)
            self.file_format = str_or_none(file_format)
            self.file_mtime = float_or_none(file_mtime)
            self.file_size = int_or_none(file_size)
            self.content = content

        Object.__init__(self, init_props=False)

    def __eq__(self, other):
        return (isinstance(other, Nut) and
                self.equality_values == other.equality_values)

    def __ne__(self, other):
        return not (self == other)

    def get_io_backend(self):
        return io.get_format_provider(self.file_format)

    def file_modified(self):
        return self.get_io_backend().get_stats(self.file_path) \
            != (self.file_mtime, self.file_size)

    @property
    def equality_values(self):
        return (
            self.file_segment, self.file_element,
            self.kind, self.codes,
            self.tmin_seconds, self.tmin_offset,
            self.tmax_seconds, self.tmax_offset, self.deltat)

    @property
    def tmin(self):
        return tjoin(self.tmin_seconds, self.tmin_offset, self.deltat)

    @property
    def tmax(self):
        return tjoin(self.tmax_seconds, self.tmax_offset, self.deltat)

    @property
    def kscale(self):
        if self.tmin_seconds is None or self.tmax_seconds is None:
            return 0
        return tscale_to_kscale(self.tmax_seconds - self.tmin_seconds)

    @property
    def waveform_kwargs(self):
        agency, network, station, location, channel, extra = \
            self.codes.split('\0')

        return dict(
            agency=agency,
            network=network,
            station=station,
            location=location,
            channel=channel,
            extra=extra,
            tmin=self.tmin,
            tmax=self.tmax,
            deltat=self.deltat)

    @property
    def station_kwargs(self):
        agency, network, station, location = self.codes.split('\0')
        return dict(
            agency=agency,
            network=network,
            station=station,
            location=location,
            tmin=self.tmin,
            tmax=self.tmax)

    @property
    def channel_kwargs(self):
        agency, network, station, location, channel = self.codes.split('\0')

        return dict(
            agency=agency,
            network=network,
            station=station,
            location=location,
            channel=channel,
            tmin=self.tmin,
            tmax=self.tmax,
            deltat=self.deltat)

    @property
    def event_kwargs(self):
        return dict(
            name=self.codes,
            time=self.tmin,
            duration=(self.tmax - self.tmin) or None)


def make_waveform_nut(
        agency='', network='', station='', location='', channel='', extra='',
        **kwargs):

    codes = '\0'.join((agency, network, station, location, channel, extra))

    return Nut(
        kind='waveform',
        codes=codes,
        **kwargs)


def make_station_nut(
        agency='', network='', station='', location='', **kwargs):

    codes = '\0'.join((agency, network, station, location))

    return Nut(
        kind='station',
        codes=codes,
        **kwargs)


def make_channel_nut(
        agency='', network='', station='', location='', channel='', **kwargs):

    codes = '\0'.join((agency, network, station, location, channel))

    return Nut(
        kind='channel',
        codes=codes,
        **kwargs)


def make_event_nut(name='', **kwargs):

    codes = name

    return Nut(
        kind='event',
        codes=codes,
        **kwargs)