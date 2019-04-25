# -*- coding: utf-8 -*-
#***********************************************************************
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
Task to edit an alignment
"""
import FreeCADGui as Gui

import Draft
import DraftTools

from DraftGui import todo

from ....alignment import horizontal_alignment

from ...support import const, utils

from ...trackers import wire_tracker

from . import edit_pi_subtask

def create(doc, view):
    """
    Class factory method
    """
    return EditAlignmentTask(doc, view)

class EditAlignmentTask:
    """
    Task to manage alignment editing
    """

    class STYLES(const.Const):
        """
        Internal constants used to define ViewObject styles
        """

        DISABLED =  [(0.4, 0.4, 0.4), 'Solid']
        ENABLED =   [(0.8, 0.8, 0.8), 'Solid']
        HIGHLIGHT = [(0.0, 1.0, 0.0), 'Solid']
        PI =        [(0.0, 0.0, 1.0), 'Solid']
        SELECTED =  [(1.0, 0.8, 0.0), 'Solid']

    def __init__(self, doc, view):

        self.panel = None
        self.view = view
        self.doc = doc
        self.tmp_group = None
        self.alignment = None
        self.points = None
        self.pi_tracker = None
        self.pi_subtask = None
        self.call = None

        self.view_objects = {
            'selectables': [],
            'line_colors': []
        }

        #disable selection entirely
        self.view.getSceneGraph().getField("selectionRole").setValue(0)

        #get all objects with LineColor and set them all to gray
        self.view_objects['line_colors'] = \
            [
                (_v.ViewObject, _v.ViewObject.LineColor)
                for _v in self.doc.findObjects()
                if hasattr(_v, 'ViewObject')
                if hasattr(_v.ViewObject, 'LineColor')
            ]

        for _v in self.view_objects['line_colors']:
            self.set_vobj_style(_v[0], self.STYLES.DISABLED)

        #create temporary group
        self.tmp_group = self.doc.addObject('App::DocumentObjectGroup', 'Temp')

        #create working, non-visual copy of horizontal alignment
        data = Gui.Selection.getSelection()[0].Proxy.get_data_copy()

        self.alignment = \
            horizontal_alignment.create(data, utils.get_uuid(), True)

        #deselect existing selections
        Gui.Selection.clearSelection()

        self.points = self.alignment.get_pi_coords()

        self.pi_subtask = \
            edit_pi_subtask.create(self.doc, self.view, self.panel,
                                   self.points)

        self.pi_tracker = \
            wire_tracker.create(self.doc, 'PI_TRACKER', self.points)

        self.tmp_group.addObject(self.alignment.Object)

        self.call = self.view.addEventCallback('SoEvent', self.action)
        #panel = DraftAlignmentTask(self.clean_up)

        #Gui.Control.showDialog(panel)
        #panel.setup()

        self.doc.recompute()
        DraftTools.redraw3DView()

    def action(self, arg):
        """
        SoEvent callback for mouse / keyboard handling
        """

        return

        #trap the escape key to quit
        if arg['Type'] == 'SoKeyboardEvent':
            if arg['Key'] == 'ESCAPE':
                print('ESCAPE!')
                self.finish()

    def set_vobj_style(self, vobj, style):
        """
        Set the view object style based on the passed style tuple
        """

        vobj.LineColor = style[0]
        vobj.DrawStyle = style[1]

    def finish(self):
        """
        Task cleanup
        """

        print('task finish')
        #reset line colors
        for _v in self.view_objects['line_colors']:
            _v[0].LineColor = _v[1]

        #re-enable selection
        self.view.getSceneGraph().getField("selectionRole").setValue(1)

        #close dialog
        if not Draft.getParam('UiMode', 1):
            Gui.Control.closeDialog()

        #remove the callback for action
        if self.call:
            self.view.removeEventCallback("SoEvent", self.call)

        #shut down the tracker
        if self.pi_tracker:
            self.pi_tracker.finalize()
            self.pi_tracker = None

        #shut down the subtask
        if self.pi_subtask:
            self.pi_subtask.finish()
            self.pi_subtask = None

        self.doc.recompute()