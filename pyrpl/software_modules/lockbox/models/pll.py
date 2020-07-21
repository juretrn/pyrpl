from .. import *
import numpy


class PllInput(InputDirect):
    slope = FloatProperty(min=-1e10, max=1e10, default=1)
    signal_at_0 = FloatProperty(min=-1e10, max=1e10, default=0)

    def expected_signal(self, variable):
        return self.slope * variable + self.signal_at_0

class FilteredInput(PllInput, InputSignal):
    """ Base class for demodulated signals. A derived class must implement
           the method expected_signal (see InputPdh in fabryperot.py for example)"""
    _gui_attributes = ['central_freq',
                       'bandwidth',
                       'quadrature_factor']
    _setup_attributes = _gui_attributes



    central_freq = FrequencyProperty(min=0.0,
                                 max=FrequencyRegister.CLOCK_FREQUENCY / 2.0,
                                 default=0.0,
                                 call_setup=True)

    quadrature_factor = IqQuadratureFactorProperty(call_setup=True)
    bandwidth = IqFilterProperty(call_setup=True)

    @property
    def acbandwidth(self):
        return self.central_freq / 128.0

    @property
    def iq(self):
        if not hasattr(self, '_iq') or self._iq is None:
            self._iq = self.pyrpl.iqs.pop(self.name)
        return self._iq

    def signal(self):
        return self.iq.name

    def _clear(self):
        self.pyrpl.iqs.free(self.iq)
        self._iq = None
        super(InputIq, self)._clear()

    def _setup(self):
        """
        setup a PDH error signal using the attribute values
        """
        self.iq.setup(frequency=self.central_freq,
                      amplitude=0,
                      phase=0,
                      input='in1',
                      gain=0,
                      bandwidth=self.bandwidth,
                      acbandwidth=self.acbandwidth,
                      quadrature_factor=self.quadrature_factor,
                      output_signal='quadrature',
                      output_direct='off')


class PfdErrorSignal(PllInput, InputSignal):
    """ Base class for demodulated signals. A derived class must implement
       the method expected_signal (see InputPdh in fabryperot.py for example)"""
    _gui_attributes = ['freq']
    _setup_attributes = _gui_attributes


    # mod_freq = ProxyProperty("iq.frequency")
    # mod_amp = ProxyProperty("iq.amplitude")
    # mod_phase = ProxyProperty("iq.phase")
    # mod_output = ProxyProperty("iq.output_direct")
    # quadrature_factor = ProxyProperty("iq.quadrature_factor")
    # bandwidth = ProxyProperty("iq.bandwidth")

    freq = FrequencyProperty(min=0.0,
                                 max=FrequencyRegister.CLOCK_FREQUENCY / 2.0,
                                 default=0.0,
                                 call_setup=True)
    bandwidth = IqFilterProperty(call_setup=False)
    quadrature_factor = IqQuadratureFactorProperty(call_setup=False)

    @property
    def acbandwidth(self):
        return self.freq / 128.0

    @property
    def iq(self):
        if not hasattr(self, '_iq') or self._iq is None:
            self._iq = self.pyrpl.iqs.pop(self.name)
        return self._iq

    def signal(self):
        return self.iq.name

    def _clear(self):
        self.pyrpl.iqs.free(self.iq)
        self._iq = None
        super(InputIq, self)._clear()

    def _setup(self):
        """
        setup a PDH error signal using the attribute values
        """
        self.iq.setup(frequency=self.freq,
                      amplitude=0,
                      phase=0,
                      input='iq1',
                      gain=0,
                      bandwidth=self.bandwidth,
                      acbandwidth=self.acbandwidth,
                      quadrature_factor=self.quadrature_factor,
                      output_signal='pfd',
                      output_direct='off')

    def sweep_acquire(self):
        """
        returns an experimental curve in V obtained from a sweep of the
        lockbox.
        """
        try:
            with self.pyrpl.scopes.pop(self.name) as scope:
                self.lockbox._sweep()
                if "sweep" in scope.states:
                    scope.load_state("sweep")
                else:
                    scope.setup(input1=self.signal(),
                                input2=self.lockbox.outputs[self.lockbox.default_sweep_output].pid.output_direct,
                                trigger_source=self.lockbox.asg.name,
                                trigger_delay=0,
                                duration=1./self.lockbox.asg.frequency,
                                ch1_active=True,
                                ch2_active=True,
                                average=True,
                                trace_average=1,
                                running_state='stopped',
                                rolling_mode=False)
                    scope.save_state("autosweep")
                curve1, curve2 = scope.curve(timeout=1./self.lockbox.asg.frequency+scope.duration)
                times = scope.times
                curve1 -= self.calibration_data._analog_offset
                return curve1, curve2, times
        except InsufficientResourceError:
            # scope is blocked
            self._logger.warning("No free scopes left for sweep_acquire. ")
            return None, None

    def calibrate(self, autosave=False):
        """
        This function should be reimplemented to measure whatever property of
        the curve is needed by expected_signal.
        """
        curve1, curve2, times = self.sweep_acquire()
        if curve1 or curve2 is None:
            self._logger.warning('Aborting calibration because no scope is available...')
            return None

        self.calibration_data.get_stats_from_curve(curve)
        # log calibration values
        self._logger.info("%s calibration successful - Min: %.3f  Max: %.3f  Mean: %.3f  Rms: %.3f",
                          self.name,
                          self.calibration_data.min,
                          self.calibration_data.max,
                          self.calibration_data.mean,
                          self.calibration_data.rms)
        # update graph in lockbox
        self.lockbox._signal_launcher.input_calibrated.emit([self])
        # save data if desired
        if autosave:
            params = self.calibration_data.setup_attributes
            params['name'] = self.name+"_calibration"
            newcurve = self._save_curve(times, curve, **params)
            self.calibration_data.curve = newcurve
            return newcurve
        else:
            return None












class Pll(Lockbox):
    wavelength = FloatProperty(max=1., min=0., default=1.064e-6, increment=1e-9)
    _gui_attributes = ['wavelength']
    _setup_attributes = _gui_attributes

    # management of intput/output units
    # setpoint_variable = 'phase'
    setpoint_unit = SelectProperty(options=['freq'],
                                   default='freq')

    _output_units = ['m', 'nm']
    # must provide conversion from setpoint_unit into all other basic units
    # management of intput/output units


    @property
    def _deg_in_m(self):
        # factor 2 comes from assumption that beam is reflected off a mirror,
        # i. e. beam gets twice the phaseshift from the displacement
        return self.wavelength / 360.0 / 2.0

    @property
    def _rad_in_m(self):
        # factor 2 comes from assumption that beam is reflected off a mirror,
        # i. e. beam gets twice the phaseshift from the displacement
        return self._rad_in_deg * self._deg_in_m

    inputs = LockboxModuleDictProperty(raw_input=InputDirect,
                                       filtered_input=FilteredInput,
                                       pfd_signal=PfdErrorSignal
                                       )

    outputs = LockboxModuleDictProperty(piezo=PiezoOutput)
                                        #piezo2=PiezoOutput)

    def set_offset_to_first_positive_edge(self):

        curve1, curve2, times = self.inputs.pfd_signal.sweep_acquire()
        negative_edges = numpy.where(numpy.diff(numpy.sign(curve1)) < 0)[0]
        positive_edges = numpy.where(numpy.diff(numpy.sign(curve1)) > 0)[0]

        if not(len(positive_edges)):
            self._logger.warning("no crossing found")
            return(None)
        offset = curve2[positive_edges[0]]
        self.outputs.piezo._setup_offset = offset
        return()









