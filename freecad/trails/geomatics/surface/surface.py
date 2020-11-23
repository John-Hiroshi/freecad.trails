# /**********************************************************************
# *                                                                     *
# * Copyright (c) 2020 Hakan Seven <hakanseven12@gmail.com>             *
# *                                                                     *
# * This program is free software; you can redistribute it and/or modify*
# * it under the terms of the GNU Lesser General Public License (LGPL)  *
# * as published by the Free Software Foundation; either version 2 of   *
# * the License, or (at your option) any later version.                 *
# * for detail see the LICENCE text file.                               *
# *                                                                     *
# * This program is distributed in the hope that it will be useful,     *
# * but WITHOUT ANY WARRANTY; without even the implied warranty of      *
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the       *
# * GNU Library General Public License for more details.                *
# *                                                                     *
# * You should have received a copy of the GNU Library General Public   *
# * License along with this program; if not, write to the Free Software *
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307*
# * USA                                                                 *
# *                                                                     *
# ***********************************************************************

'''
Create a Surface Object from FPO.
'''

import FreeCAD, FreeCADGui
from pivy import coin
from .surface_func import SurfaceFunc
from freecad.trails import ICONPATH, geo_origin
from . import surfaces
import random, copy



def create(points=[], name='Surface'):
    group = surfaces.get()
    obj=FreeCAD.ActiveDocument.addObject("App::FeaturePython", "Surface")
    obj.Label = name
    Surface(obj)
    obj.Points = points
    ViewProviderSurface(obj.ViewObject)
    group.addObject(obj)
    FreeCAD.ActiveDocument.recompute()

    return obj


class Surface(SurfaceFunc):
    """
    This class is about Surface Object data features.
    """

    def __init__(self, obj):
        '''
        Set data properties.
        '''
        self.Type = 'Trails::Surface'

        # Triangulation properties.
        obj.addProperty(
            "App::PropertyVectorList",
            "Points",
            "Base",
            "List of group points").Points = []

        obj.addProperty(
            "App::PropertyIntegerList",
            "Delaunay",
            "Base",
            "Index of Delaunay vertices").Delaunay = []

        obj.addProperty(
            "App::PropertyIntegerList",
            "Triangles",
            "Base",
            "Index of triangles vertices").Triangles = []

        obj.addProperty(
            "App::PropertyLength",
            "MaxLength",
            "Base",
            "Maximum length of triangle edge").MaxLength = 50000

        obj.addProperty(
            "App::PropertyAngle",
            "MaxAngle",
            "Base",
            "Maximum angle of triangle edge").MaxAngle = 170

        # Contour properties.
        obj.addProperty(
            "App::PropertyFloatConstraint",
            "ContourInterval",
            "Point Style",
            "Size of the point group").ContourInterval = (1.0, 0.0, 100.0, 1.0)

        obj.addProperty(
            "App::PropertyVectorList",
            "ContourPoints",
            "Surface Style",
            "Points of contours", 4).ContourPoints = []

        obj.addProperty(
            "App::PropertyIntegerList",
            "ContourVertices",
            "Surface Style",
            "Vertices of contours.", 4).ContourVertices = []

        obj.Proxy = self

    def onChanged(self, obj, prop):
        '''
        Do something when a data property has changed.
        '''
        points = obj.getPropertyByName("Points")
        lmax = obj.getPropertyByName("MaxLength")
        amax = obj.getPropertyByName("MaxAngle")
        deltaH = obj.getPropertyByName("ContourInterval")

        if prop =="Points":
            if points:
                obj.Delaunay = self.triangulate(points)

        if prop == "Delaunay" or prop == "MaxLength" or prop == "MaxAngle":
            delaunay = obj.getPropertyByName("Delaunay")

            if points and delaunay:
                triangles = self.test_delaunay(
                    points, delaunay, lmax, amax)

                obj.Triangles = triangles

        if prop == "Points" or prop == "Triangles" or prop == "ContourInterval":
            triangles = obj.getPropertyByName("Triangles")

            if points:
                origin = geo_origin.get(points[0])

                coords, num_vert = self.contour_points(
                    points, triangles, deltaH)

                obj.ContourPoints = coords
                obj.ContourVertices = num_vert

    def execute(self, obj):
        '''
        Do something when doing a recomputation. 
        '''
        return

class ViewProviderSurface:
    """
    This class is about Surface Object view features.
    """

    def __init__(self, vobj):
        '''
        Set view properties.
        '''
        (r, g, b) = (random.random(),
                     random.random(),
                     random.random())

        vobj.addProperty(
            "App::PropertyColor",
            "TriangleColor",
            "Surface Style",
            "Color of the point group").TriangleColor = (r, g, b)

        vobj.Proxy = self

    def attach(self, vobj):
        '''
        Create Object visuals in 3D view.
        '''
        # GeoCoords Node.
        self.geo_coords = coin.SoGeoCoordinate()

        # Surface features.
        self.triangles = coin.SoIndexedFaceSet()
        shape_hints = coin.SoShapeHints()
        shape_hints.vertex_ordering = coin.SoShapeHints.COUNTERCLOCKWISE
        self.mat_color = coin.SoMaterial()
        mat_binding = coin.SoMaterialBinding()
        mat_binding.value = coin.SoMaterialBinding.OVERALL
        edge_color = coin.SoBaseColor()
        edge_color.rgb = (0.5, 0.5, 0.5)
        offset = coin.SoPolygonOffset()

        # Highlight for selection.
        highlight = coin.SoType.fromName('SoFCSelection').createInstance()
        #highlight.documentName.setValue(FreeCAD.ActiveDocument.Name)
        #highlight.objectName.setValue(vobj.Object.Name)
        #highlight.subElementName.setValue("Main")
        highlight.addChild(self.geo_coords)
        highlight.addChild(self.triangles)

        # Line style.
        line_style = coin.SoDrawStyle()
        line_style.style = coin.SoDrawStyle.LINES
        line_style.lineWidth = 2

        # Contour features.
        cont_color = coin.SoBaseColor()
        cont_color.rgb = (1, 1, 0)
        self.cont_coords = coin.SoGeoCoordinate()
        self.cont_lines = coin.SoLineSet()

        # Contour root.
        contours = coin.SoSeparator()
        contours.addChild(cont_color)
        contours.addChild(line_style)
        contours.addChild(self.cont_coords)
        contours.addChild(self.cont_lines)

        # Edge root.
        edges = coin.SoSeparator()
        edges.addChild(edge_color)
        edges.addChild(line_style)
        edges.addChild(highlight)

        # Surface root.
        surface_root = coin.SoSeparator()
        surface_root.addChild(edges)
        surface_root.addChild(offset)
        surface_root.addChild(shape_hints)
        surface_root.addChild(contours)
        surface_root.addChild(self.mat_color)
        surface_root.addChild(mat_binding)
        surface_root.addChild(highlight)
        vobj.addDisplayMode(surface_root,"Surface")

        # Take features from properties.
        self.onChanged(vobj,"TriangleColor")

    def onChanged(self, vobj, prop):
        '''
        Update Object visuals when a view property changed.
        '''
        try:
            if prop == "TriangleColor":
                color = vobj.getPropertyByName("TriangleColor")
                self.mat_color.diffuseColor = (color[0],color[1],color[2])
        except Exception: pass

    def updateData(self, obj, prop):
        '''
        Update Object visuals when a data property changed.
        '''
        if prop == "Points":
            points = obj.getPropertyByName("Points")
            if points:
                # Get GeoOrigin.
                origin = geo_origin.get(points[0])

                # Set GeoCoords.
                geo_system = ["UTM", origin.UtmZone, "FLAT"]
                self.geo_coords.geoSystem.setValues(geo_system)
                self.geo_coords.point.values = points

                #Set contour system.
                self.cont_coords.geoSystem.setValues(geo_system)

        if prop == "Triangles":
            triangles = obj.getPropertyByName("Triangles")
            self.triangles.coordIndex.values = triangles

        if prop == "Points" or prop == "Triangles" or prop == "ContourInterval":
            cont_points = obj.getPropertyByName("ContourPoints")
            cont_vert = obj.getPropertyByName("ContourVertices")

            self.cont_coords.point.values = cont_points
            self.cont_lines.numVertices.values = cont_vert

    def getDisplayModes(self,vobj):
        '''
        Return a list of display modes.
        '''
        modes=[]
        modes.append("Surface")

        return modes

    def getDefaultDisplayMode(self):
        '''
        Return the name of the default display mode.
        '''
        return "Surface"

    def setDisplayMode(self,mode):
        '''
        Map the display mode defined in attach with 
        those defined in getDisplayModes.
        '''
        return mode

    def getIcon(self):
        '''
        Return object treeview icon.
        '''
        return ICONPATH + '/icons/Surface.svg'

    def __getstate__(self):
        """
        Save variables to file.
        """
        return None
 
    def __setstate__(self,state):
        """
        Get variables from file.
        """
        return None