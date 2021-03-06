#------------------------------------------------------------------------------
# Copyright (c) 2005, Enthought, Inc.
# All rights reserved.
# 
# This software is provided without warranty under the terms of the BSD
# license included in enthought/LICENSE.txt and may be redistributed only
# under the conditions described in the aforementioned license.  The license
# is also available online at http://www.enthought.com/licenses/BSD.txt
# Thanks for using Enthought open source!
# 
# Author: Enthought, Inc.
# Description: <Enthought pyface package component>
#------------------------------------------------------------------------------
""" A widget for editing Python code. """


# Enthought library imports.
from enthought.traits.api import Bool, Event, Interface, Unicode

# Local imports.
from key_pressed_event import KeyPressedEvent


class IPythonEditor(Interface):
    """ A widget for editing Python code. """

    #### 'IPythonEditor' interface ############################################
    
    # Has the file in the editor been modified?
    dirty = Bool(False)

    # The pathname of the file being edited.
    path = Unicode

    # Should line numbers be shown in the margin?
    show_line_numbers = Bool(True)

    #### Events ####

    # The contents of the editor has changed.
    changed = Event

    # A key has been pressed.
    key_pressed = Event(KeyPressedEvent)
    
    ###########################################################################
    # 'IPythonEditor' interface.
    ###########################################################################
    
    def load(self, path=None):
        """ Loads the contents of the editor. """

    def save(self, path=None):
        """ Saves the contents of the editor. """

    # FIXME v3: This is very dependent on the underlying implementation.
    def set_style(self, n, fore, back):
        """ Set the foreground and background colors for a particular style and
        set the font and size to default values.
        """

    def select_line(self, lineno):
        """ Selects the specified line. """


class MPythonEditor(object):
    """ The mixin class that contains common code for toolkit specific
    implementations of the IPythonEditor interface.

    Implements: _changed_path()
    """

    def _changed_path(self):
        """ Called when the path to the file is changed. """

        if self.control is not None:
            self.load()

        return

#### EOF ######################################################################
