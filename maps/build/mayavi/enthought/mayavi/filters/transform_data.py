"""Performs a linear transformation to input data using a
tvtk.BoxWidget.  This does not work with
ImageData/StructuredPoints/RectilinearGrid.

"""
# Author: Prabhu Ramachandran <prabhu@aero.iitb.ac.in>
# Copyright (c) 2006,  Enthought, Inc.
# License: BSD Style.

# Standard library imports.
import cPickle

# Enthought library imports.
from enthought.traits.api import Instance, Property, Bool, Int, \
     Trait, TraitMap, Button
from enthought.traits.ui.api import View, Group, Item
from enthought.tvtk.api import tvtk
from enthought.persistence import state_pickler

# Local imports
from enthought.mayavi.core.filter import Filter
from enthought.mayavi.core.common import error
from enthought.mayavi.core.pipeline_info import PipelineInfo


######################################################################
# `TransformData` class.
######################################################################
class TransformData(Filter):
    """Performs a linear transformation to input data using a
    tvtk.BoxWidget.  This does not work with
    ImageData/StructuredPoints/RectilinearGrid.
    """

    # The version of this class.  Used for persistence.
    __version__ = 0

    # The widget that we use to perform the transformation.
    widget = Instance(tvtk.ThreeDWidget, allow_none=False, record=True)

    # The filter we manage.
    filter = Instance(tvtk.Object, allow_none=False)

    # The transform.
    transform = Property

    # Update the data immediately or at the end of the interaction.
    update_mode = Trait('semi-interactive',
                        TraitMap({'interactive':'InteractionEvent',
                                  'semi-interactive': 'EndInteractionEvent'}),
                        desc='speed at which the data should be updated')

    input_info = PipelineInfo(datasets=['poly_data', 
                                        'structured_grid',
                                        'unstructured_grid'],
                              attribute_types=['any'],
                              attributes=['any'])

    output_info = PipelineInfo(datasets=['poly_data', 
                                         'structured_grid',
                                         'unstructured_grid'],
                               attribute_types=['any'],
                               attributes=['any'])

    ########################################
    # View related code.

    # Reset the transformation.
    reset = Button("Reset Transformation")

    view = View(Group(Group(Item('update_mode'),
                            ),
                      Group(Item('reset'),
                            Item(name='widget', style='custom', resizable=True),
                            show_labels=False
                            )
                      ),
                resizable=True
                )

    ########################################
    # Private traits.
    _transform = Instance(tvtk.Transform, allow_none=False)

    _first = Bool(True)

    _observer_id = Int(-1)

    ######################################################################
    # `object` interface.
    ######################################################################
    def __get_pure_state__(self):
        d = super(TransformData, self).__get_pure_state__()
        for name in ('_first', '_observer_id'):
            d.pop(name, None)
        d['matrix'] = cPickle.dumps(self._transform.matrix)
        return d

    def __set_pure_state__(self, state):
        mat = state.pop('matrix')
        super(TransformData, self).__set_pure_state__(state)
        state_pickler.set_state(self, state)
        self._transform.set_matrix(cPickle.loads(mat))
        self.widget.set_transform(self._transform)

    ######################################################################
    # `Filter` interface.
    ######################################################################
    def setup_pipeline(self):
        self._transform = tvtk.Transform()
        self.widget = tvtk.BoxWidget(place_factor=1.1)
        self.filter = tvtk.TransformFilter()        
        super(TransformData, self).setup_pipeline()

    def update_pipeline(self):
        # Do nothing if there is no input.
        inputs = self.inputs
        if len(inputs) == 0:
            return

        inp = inputs[0].outputs[0]
        if inp.is_a('vtkImageData') or inp.is_a('vtkRectilinearGrid'):
            error('Transformation not supported for '\
                  'ImageData/StructuredPoints/RectilinearGrid')
            return
        
        # Set the input for the widget and place it if this hasn't
        # been done before.
        w = self.widget
        w.input = inp
        if self._first:
            w.place_widget()
            self._first = False
        
        # By default we set the input to the first output of the first
        # input.
        fil = self.filter
        fil.input = inp
        fil.transform = self._transform
        fil.update()
        self._set_outputs([fil.output])

    def update_data(self):
        # Do nothing if there is no input.
        if len(self.inputs) == 0:
            return

        self.filter.update()
        # Propagate the data_changed event.
        self.data_changed = True

    ######################################################################
    # Non-public interface.
    ######################################################################
    def _get_transform(self):
        return self._transform

    def _on_interaction_event(self, obj, event):
        tfm = self._transform
        self.widget.get_transform(tfm)
        f = self.filter
        f.transform = tfm
        f.update()
        self.render()
        recorder = self.recorder
        if recorder is not None:
            state = {}
            state['elements'] = tfm.matrix.__getstate__()['elements']
            name = recorder.get_script_id(self)
            recorder.record('%s.transform.matrix.__setstate__(%s)'\
                            %(name, state))
            recorder.record('%s.widget.set_transform(%s.transform)'\
                            %(name, name))
            recorder.record('%s.filter.update()'%name)
    
    def _widget_changed(self, old, new):
        if old is not None:
            old.on_trait_change(self.render, remove=True)
            old.remove_observer(self._observer_id)
            self.widgets.remove(old)
        new.on_trait_change(self.render)
        self._observer_id = new.add_observer(self.update_mode_,
                                             self._on_interaction_event)
        self.widgets.append(new)
        if len(self.inputs) > 0:
            new.input = self.inputs[0].output[0]
        
    def _filter_changed(self, old, new):
        if old is not None:
            old.on_trait_change(self.render, remove=True)
        new.on_trait_change(self.render)
        transform = self.transform
        if transform is not None:
            new.transform = transform
        if len(self.inputs) > 0:
            inp = self.inputs[0].outputs[0]
            new.input = inp
            self.outputs = [new.output]

    def _reset_fired(self):
        self._transform.identity()
        self.widget.place_widget()
        self.filter.update()
        self.render()

    def _update_mode_changed(self, old, new):        
        w = self.widget
        if w is not None:
            w.remove_observer(self._observer_id)
            self._observer_id = w.add_observer(self.update_mode_,
                                               self._on_interaction_event)
            self.render()
