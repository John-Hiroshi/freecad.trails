# -*- coding: utf-8 -*-
#**************************************************************************
#*                                                                     *
#* Copyright (c) 2019 Joel Graff <monograff76@gmail.com>               *
#*                                                                     *
#* This program is free software; you can redistribute it and/or modify*
#* it under the terms of the GNU Lesser General Public License (LGPL)  *
#* as published by the Free Software Foundation; either version 2 of   *
#* the License, or (at your option) any later version.                 *
#* for detail see the LICENCE text file.                               *
#*                                                                     *
#* This program is distributed in the hope that it will be useful,     *
#* but WITHOUT ANY WARRANTY; without even the implied warranty of      *
#* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the       *
#* GNU Library General Public License for more details.                *
#*                                                                     *
#* You should have received a copy of the GNU Library General Public   *
#* License along with this program; if not, write to the Free Software *
#* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307*
#* USA                                                                 *
#*                                                                     *
#***********************************************************************
"""
Tracker for alignment editing
"""

from pivy import coin

from FreeCAD import Vector

import FreeCADGui as Gui

from .base_tracker import BaseTracker

from ..support.mouse_state import MouseState
from ..support.view_state import ViewState

from .node_tracker import NodeTracker
from .wire_tracker import WireTracker
from .curve_tracker import CurveTracker

class AlignmentTracker(BaseTracker):
    """
    Tracker class for alignment design
    """

    def __init__(self, doc, object_name, alignment, datum=Vector()):
        """
        Constructor
        """

        self.alignment = alignment
        self.doc = doc
        self.names = [doc.Name, object_name, 'ALIGNMENT_TRACKER']
        self.user_dragging = False
        self.status_bar = Gui.getMainWindow().statusBar()
        self.pi_list = []
        self.datum = alignment.model.data.get('meta').get('Start')
        self.drag_curves = []

        #base (placement) transformation for the alignment
        self.transform = coin.SoTransform()
        self.transform.translation.setValue(
            tuple(alignment.model.data.get('meta').get('Start'))
        )
        super().__init__(names=self.names, children=[self.transform])

        #scenegraph node structure for editing and dragging operations
        self.groups = {
            'EDIT': coin.SoGroup(),
            'DRAG': coin.SoGroup(),
            'SELECTED': coin.SoSeparator(),
            'PARTIAL': coin.SoSeparator(),
        }

        self.state.draggable = True

        self.drag_transform = coin.SoTransform()

        #add two nodes to the drag group - the transform and a dummy node
        #which provides a way to access the transform matrix
        self.groups['SELECTED'].addChild(self.drag_transform)
        self.groups['SELECTED'].addChild(coin.SoSeparator())

        self.groups['DRAG'].addChild(self.groups['SELECTED'])
        self.groups['DRAG'].addChild(self.groups['PARTIAL'])

        self.node.addChild(self.groups['EDIT'])
        self.node.addChild(self.groups['DRAG'])

        #generate initial node trackers and wire trackers for mouse interaction
        #and add them to the scenegraph
        self.trackers = None
        self.build_trackers()

        _trackers = []
        for _v in self.trackers.values():
            _trackers.extend(_v)

        for _v in _trackers:
            self.insert_node(_v.switch, self.groups['EDIT'])

        #insert in the scenegraph root
        self.insert_node(self.switch)

    def _update_status_bar(self):
        """
        Update the status bar with the latest mouseover data
        """

        self.status_bar.showMessage(
            MouseState().component + ' ' + str(tuple(MouseState().coordinates))
        )

    def start_drag(self):
        """
        Override base function
        """

        pass

    def on_drag(self):
        """
        Override base function
        """

        if not MouseState().button1.dragging:
            return

        print(self.name, 'drag curves = ', self.drag_curves)

        #get the list of tangents
        _tans = [0.0] \
            + [_v.drag_arc['Tangent'] for _v in self.drag_curves] + [0.0]

        print('tangents', _tans)
        #enumerate all but the last tangent,
        #getting the curve one in
        for _i, _v in enumerate(_tans[:-2]):
            self.drag_curves[_i].validate(lt_tan=_v, rt_tan=_tans[_i + 2])

    def end_drag(self):
        """
        Override base fucntion
        """

        print(self.name, 'end drag')
        self.drag_curves = []

    def button_event(self, arg):
        """
        Override base button actions
        """

        #multi-select
        _pick = MouseState().component

        if not _pick:
            return

        if MouseState().button1.state == 'UP':
            return

        _i = 0

        #abort if nodes are selected - this routine is only for multi-selecting
        for _v in self.trackers['Nodes']:

            if _v.state.selected.value:
                _i += 1

        if MouseState().ctrlDown and _i > 1:
            return

        elif _i > 0:
            return

        #if a curve is picked, set the visibility ignore flag on, so the
        #curve PI doesn't get redrawn
        #if 'CURVE' in _pick:

        #    _idx = int(_pick.split('-')[1])

        #    self.trackers['Nodes'][_idx + 1].state.visible.ignore = True

        if 'NODE' in _pick:

            print(self.name, 'button', MouseState().component)

            _idx = int(_pick.split('-')[1])

            _nodes = [self.trackers['Nodes'][_idx]]

            if MouseState().ctrlDown:
                _nodes = self.trackers['Nodes'][_idx:]

            for _v in _nodes:
                _v.state.selected.value = True
                _v.state.selected.ignore_once()

            _lower = max(0, _idx - 2)

            _max = 1

            if MouseState().ctrlDown:
                _max = 0

            _upper = min(len(self.trackers['Curves']), _idx + _max)

            print('picking curves ', _lower, _upper)

            for _i in range(_lower, _upper):
                self.drag_curves.append(self.trackers['Curves'][_i])

    def build_trackers(self):
        """
        Build the node and wire trackers that represent the selectable
        portions of the alignment geometry
        """

        _model = self.alignment.model.data

        #build a list of coordinates from curves in the geometry
        _nodes = [Vector()]

        for _geo in _model.get('geometry'):

            if _geo.get('Type') != 'Line':
                _nodes += [_geo.get('PI')]

        _nodes += [_model.get('meta').get('End')]

        #build the trackers
        _names = self.names[:2]
        _result = {'Nodes': [], 'Tangents': [], 'Curves': []}

        #node trackers
        for _i, _pt in enumerate(_nodes):

            _tr = NodeTracker(
                names=_names[:2] + ['NODE-' + str(_i)], point=_pt
            )
            _result['Nodes'].append(_tr)

        _result['Nodes'][0].is_end_node = True
        _result['Nodes'][-1].is_end_node = True

        #wire trackers - Tangents
        for _i in range(0, len(_result['Nodes']) - 1):

            _nodes = _result['Nodes'][_i:_i + 2]

            _result['Tangents'].append(
                self._build_wire_tracker(
                    wire_name=_names[:2] + ['WIRE-' + str(_i)],
                    nodes=_nodes,
                    points=[],
                    select=False
                )
            )

        _curves = self.alignment.get_curves()
        _names = self.names[:2]

        #curve trackers
        for _i in range(0, len(_result['Tangents']) - 1):

            _ct = CurveTracker(
                names=_names[:2] + ['CURVE-' + str(_i)],
                curve=_curves[_i],
                pi_nodes=_result['Nodes'][_i:_i+3]
            )

            _ct.set_selectability(True)

            _result['Nodes'][_i + 1].conditions.append(_ct.name)
            _result['Curves'].append(_ct)

        self.trackers = _result

    def _build_wire_tracker(self, wire_name, nodes, points, select=False):
        """
        Convenience function for WireTracker construction
        """

        _wt = WireTracker(names=wire_name)

        _wt.set_selectability(select)
        _wt.set_points(points, nodes)
        _wt.update()

        return _wt

    def finalize(self):
        """
        Cleanup the tracker
        """

        for _t in self.trackers.values():

            for _u in _t:
                _u.finalize()

        self.remove_node(self.groups['EDIT'], self.node)
        self.remove_node(self.groups['DRAG'], self.node)

        if self.callbacks:
            for _k, _v in self.callbacks.items():
                ViewState().view.removeEventCallback(_k, _v)

            self.callbacks.clear()

        super().finalize()
