# This file defines the AngleFormatterLocator class which is a class that
# provides both a method for a formatter and one for a locator, for a given
# label spacing. The advantage of keeping the two connected is that we need to
# make sure that the formatter can correctly represent the spacing requested and
# vice versa. For example, a format of dd:mm cannot work with a tick spacing
# that is not a multiple of one arcminute.

import re
import warnings

import numpy as np

from astropy import units as u
from astropy.coordinates import Angle


DMS_RE = re.compile('^dd(:mm(:ss(.(s)+)?)?)?$')
HMS_RE = re.compile('^hh(:mm(:ss(.(s)+)?)?)?$')
DDEC_RE = re.compile('^d(.(d)+)?$')
SCAL_RE = re.compile('^x(.(x)+)?$')


class BaseFormatterLocator(object):
    """
    A joint formatter/locator
    """

    def __init__(self, values=None, number=None, spacing=None, format=None):

        self._values = values
        self._number = number
        self._spacing = spacing
        self.format = format

        if values is None and number is None and spacing is None:
            self._number = 5

    @property
    def values(self):
        return self._values

    @values.setter
    def values(self, values):
        self._number = None
        self._spacing = None
        self._values = values

    @property
    def number(self):
        return self._number

    @number.setter
    def number(self, number):
        self._number = number
        self._spacing = None
        self._values = None

    @property
    def spacing(self):
        return self._spacing

    @spacing.setter
    def spacing(self, spacing):
        if not isinstance(spacing, u.Quantity):
            raise TypeError("spacing should be a quantity")
        self._number = None
        self._spacing = spacing
        self._values = None


class AngleFormatterLocator(BaseFormatterLocator):
    """
    A joint formatter/locator
    """

    def __init__(self, values=None, number=None, spacing=None, format='dd:mm:ss'):
        super(AngleFormatterLocator, self).__init__(values=values,
                                                    number=number,
                                                    spacing=spacing,
                                                    format=format)

    @property
    def format(self):
        return self._format

    @format.setter
    def format(self, value):

        self._format = value

        if DMS_RE.match(value) is not None:
            self._decimal = False
            self._unit = u.degree
            if '.' in value:
                self._precision = len(value) - value.index('.') - 1
                self._fields = 3
            else:
                self._precision = 0
                self._fields = value.count(':') + 1
        elif HMS_RE.match(value) is not None:
            self._decimal = False
            self._unit = u.hourangle
            if '.' in value:
                self._precision = len(value) - value.index('.')
                self._fields = 3
            else:
                self._precision = 0
                self._fields = value.count(':') + 1
        elif DDEC_RE.match(value) is not None:
            self._decimal = True
            self._unit = u.degree
            self._fields = 1
            if '.' in value:
                self._precision = len(value) - value.index('.')
            else:
                self._precision = 0
        else:
            raise ValueError("Invalid format: {0}".format(value))

        if self.spacing is not None and self.spacing < self.base_spacing:
            warnings.warn("Spacing is too small - resetting spacing to match format")
            self.spacing = self.base_spacing

        if self.spacing is not None and (self.spacing % self.base_spacing) > 1e-10 * u.deg:
            warnings.warn("Spacing is not a multiple of base spacing - resetting spacing to match format")
            self.spacing = self.base_spacing * np.round(self.spacing / self.spacing)

    @property
    def base_spacing(self):

        if self._decimal:

            spacing = u.degree / (10. ** self._precision)

        else:

            if self._fields == 1:
                spacing = 1. * u.degree
            elif self._fields == 2:
                spacing = 1. * u.arcmin
            elif self._fields == 3:
                if self._precision == 0:
                    spacing = 1. * u.arcsec
                else:
                    spacing = u.arcsec / (10. ** self._precision)

        if self._unit is u.hourangle:
            spacing *= 15

        return spacing

    def locator(self, value_min, value_max):

        if self.values is not None:

            # values were manually specified
            return np.asarray(self.values)

        else:

            if self.spacing is not None:

                # spacing was manually specified
                spacing_deg = self.spacing.to(u.degree).value

            elif self.number is not None:

                # number of ticks was specified, work out optimal spacing

                # first compute the exact spacing
                dv = abs(float(value_max - value_min)) / self.number * u.degree

                if dv < self.base_spacing:
                    # if the spacing is less than the minimum spacing allowed by the format, simply
                    # use the format precision instead.
                    spacing_deg = self.base_spacing.to(u.degree).value
                else:
                    # otherwise we clip to the nearest 'sensible' spacing
                    if self._unit is u.degree:
                        from .utils import select_step_degree
                        spacing_deg = select_step_degree(dv).to(u.degree).value
                    else:
                        from .utils import select_step_hour
                        spacing_deg = select_step_hour(dv).to(u.degree).value

            # We now find the interval values as multiples of the spacing and generate the tick
            # positions from this
            imin = np.floor(value_min / spacing_deg)
            imax = np.ceil(value_max / spacing_deg)
            values = np.arange(imin, imax + 1, dtype=int) * spacing_deg
            return values

    def formatter(self, values):
        if len(values) > 0:
            angles = Angle(np.asarray(values), unit=u.deg)
            string = angles.to_string(unit=self._unit,
                                      precision=self._precision,
                                      decimal=self._decimal,
                                      fields=self._fields).tolist()
            return string
        else:
            return []


class ScalarFormatterLocator(BaseFormatterLocator):
    """
    A joint formatter/locator
    """

    def __init__(self, values=None, number=None, spacing=None, format='x.xxx'):
        super(ScalarFormatterLocator, self).__init__(values=values,
                                                     number=number,
                                                     spacing=spacing,
                                                     format=format)

    @property
    def format(self):
        return self._format

    @format.setter
    def format(self, value):

        self._format = value

        if SCAL_RE.match(value) is not None:
            if '.' in value:
                self._precision = len(value) - value.index('.')
            else:
                self._precision = 0
        else:
            raise ValueError("Invalid format: {0}".format(value))

        if self.spacing is not None and self.spacing < self.base_spacing:
            warnings.warn("Spacing is too small - resetting spacing to match format")
            self.spacing = self.base_spacing

        if self.spacing is not None and (self.spacing % self.base_spacing) > 1e-10:
            warnings.warn("Spacing is not a multiple of base spacing - resetting spacing to match format")
            self.spacing = self.base_spacing * np.round(self.spacing / self.spacing)

    @property
    def base_spacing(self):
        return 1. / (10. ** self._precision)

    def locator(self, value_min, value_max):

        if self.values is not None:

            # values were manually specified
            return np.asarray(self.values)

        else:

            if self.spacing is not None:

                # spacing was manually specified
                spacing = self.spacing

            elif self.number is not None:

                # number of ticks was specified, work out optimal spacing

                # first compute the exact spacing
                dv = abs(float(value_max - value_min)) / self.number

                if dv < self.base_spacing:
                    # if the spacing is less than the minimum spacing allowed by the format, simply
                    # use the format precision instead.
                    spacing = self.base_spacing
                else:
                    from .utils import select_step_scalar
                    spacing = select_step_scalar(dv)

            # We now find the interval values as multiples of the spacing and generate the tick
            # positions from this
            imin = np.floor(value_min / spacing)
            imax = np.ceil(value_max / spacing)
            values = np.arange(imin, imax + 1, dtype=int) * spacing
            return values

    def formatter(self, values):
        if len(values) > 0:
            return [("{0:." + str(self._precision) + "f}").format(x) for x in values]
        else:
            return []