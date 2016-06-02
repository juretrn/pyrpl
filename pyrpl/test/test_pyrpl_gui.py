from nose.tools import with_setup
from unittest import TestCase
import os
import numpy as np
import logging
from pyrpl.gui.pyrpl_gui import ComboProperty, BoolProperty, \
                                APP, NumberProperty

logger = logging.getLogger(name=__name__)

from pyrpl.gui import RedPitayaGui
from PyQt4.QtTest import QTest
from PyQt4.QtCore import Qt, QPoint

class TestClass(object):
    @classmethod
    def setUpAll(self):
        # these tests wont succeed without the hardware
        #if os.environ['REDPITAYA_HOSTNAME'] == 'unavailable':
        #    self.r = None
        #else:
        self.r = RedPitayaGui()
        self.r.gui()

    def test_scope_gui(self):
        if self.r is None:
            return
        scope_widget = self.r.scope_widget
        for prop in self.r.scope_widget.properties:
            if isinstance(prop, ComboProperty):
                for option in prop.options:
                    to_set = prop.widget.findText(str(option))
                    prop.widget.setCurrentIndex(to_set)
                    assert (getattr(self.r.scope, prop.name)==option)
            elif isinstance(prop, BoolProperty):
                for i in range(2):
                    QTest.mouseClick(prop.widget, Qt.LeftButton)
                    assert (getattr(self.r.scope, prop.name)\
                            ==(prop.widget.checkState()==2))
            elif isinstance(prop, NumberProperty):
                for i in range(3):
                    prop.widget.stepUp()
                    assert(abs(getattr(self.r.scope, prop.name) - \
                           prop.widget.value())<0.0001)

    def test_asg_gui(self):
        if self.r is None:
            return
        for asg_widget in self.r.all_asg_widget.asg_widgets:
            self.try_gui_module(asg_widget)


    def try_gui_module(self, module_widget): # name should not start with test
        module = module_widget.module
        for prop in module_widget.properties:
            if isinstance(prop, ComboProperty):
                for option in prop.options:
                    to_set = prop.widget.findText(str(option))
                    prop.widget.setCurrentIndex(to_set)
                    assert (getattr(module, prop.name) == option)
            elif isinstance(prop, BoolProperty):
                for i in range(2):
                    QTest.mouseClick(prop.widget, Qt.LeftButton)
                    assert (getattr(module, prop.name) \
                            == (prop.widget.checkState() == 2))
            elif isinstance(prop, NumberProperty):
                for i in range(3):
                    prop.widget.stepUp()
                    val = getattr(module, prop.name)
                    wid_val = prop.widget.value()
                    err = abs((val - wid_val)/max(val,1.))
                    assert(err < 0.001)
