# buggy in the sense that you must first apply all transforms 
# / scale /location / rotation, to a mesh.

'''
by Dealga McArdle, july 2011.

BEGIN GPL LICENSE BLOCK

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software Foundation,
Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

END GPL LICENCE BLOCK
'''

import bpy
import bgl
import blf
import mathutils
import bpy_extras
import math

from mathutils import Vector
from mathutils.geometry import interpolate_bezier as bezlerp
from bpy_extras.view3d_utils import location_3d_to_region_2d as loc3d2d


# note to the user: several of my methods here are probably not 'best practice'
# please temper your perception of the script with the knowledge that it is 
# an experiment that got a little out of hand.


''' temporary constants, switches '''

KAPPA = 4 * (( math.sqrt(2) - 1) / 3 )
DRAW_POINTS = True
DEBUG = False

gl_col1 = 1.0, 0.2, 0.2, 1.0  # vertex arc color
gl_col2 = 0.5, 0.7, 0.4, 1.0  # radial center color

BUILD_REV = int(bpy.app.build_revision)
CHANGE_REV = 38676


''' helper functions '''


def find_index_of_selected_vertex(obj):

    selected_verts = [i.index for i in obj.data.vertices if i.select]
    
    # prevent script from operating if currently >1 vertex is selected.
    verts_selected = len(selected_verts)
    if verts_selected != 1:
        return None
    else:
        return selected_verts[0]



def find_connected_verts(obj, found_index):

    edges = obj.data.edges
    connecting_edges = [i for i in edges if found_index in i.vertices[:]]
    if len(connecting_edges) != 2:
        return None
    else:
        connected_verts = []
        for edge in connecting_edges:
            cvert = set(edge.vertices[:]) 
            cvert.remove(found_index)
            connected_verts.append(cvert.pop())
        return connected_verts


def return_connected_from_object(obj):
    # this function should only be called when it will return the correct 
    # and expected result. it's ugly, but OK for now.
    f_index = find_index_of_selected_vertex(obj)
    return find_connected_verts(obj, f_index)



def find_distances(obj, connected_verts, found_index):
    edge_lengths = []
    for vert in connected_verts:
        co1 = obj.data.vertices[vert].co
        co2 = obj.data.vertices[found_index].co
        edge_lengths.append([vert, (co1-co2).length])
    return edge_lengths

    
    
def generate_fillet(obj, c_index, max_rad, f_index):
        
    def get_first_cut(outer_point, focal, distance_from_f):
        co1 = obj.data.vertices[focal].co
        co2 = obj.data.vertices[outer_point].co
        real_length = (co1-co2).length
        ratio = distance_from_f / real_length
        
        # must use new variable, cannot do co1 += obj_center, changes in place.
        new_co1 = co1 + obj_centre
        new_co2 = co2 + obj_centre        
        return new_co1.lerp(new_co2, ratio)
        
    obj_centre = obj.location
    distance_from_f = max_rad * bpy.context.scene.MyMove

    # make imaginary line between outerpoints
    outer_points = []
    for point in c_index:
        outer_points.append(get_first_cut(point, f_index, distance_from_f))
 
    # make imaginary line from focal point to halfway between outer_points
    focal_coordinate = obj.data.vertices[f_index].co + obj_centre
    center_of_outer_points = (outer_points[0] + outer_points[1]) / 2
    
    # find radial center, by lerping ab -> ad
    BC = (center_of_outer_points-outer_points[1]).length
    AB = (focal_coordinate-center_of_outer_points).length
    BD = (BC/AB)*BC
    AD = AB + BD
    ratio = AD / AB
    radial_center = focal_coordinate.lerp(center_of_outer_points, ratio)
        
    guide_line = [focal_coordinate, radial_center]
    return outer_points, guide_line



def get_correct_verts(arc_centre, arc_start, arc_end, NUM_VERTS, context):
        
    obj_centre = context.object.location
    axis = mathutils.geometry.normal(arc_centre, arc_end, arc_start)
 
    point1 = arc_start - arc_centre
    point2 = arc_end - arc_centre
    main_angle = point1.angle(point2)
    main_angle_degrees = math.degrees(main_angle)

    div_angle = main_angle / (NUM_VERTS - 1)

    if DEBUG:
        print("arc_centre =", arc_centre)
        print("arc_start =", arc_start)
        print("arc_end =", arc_end)
        print("NUM_VERTS =", NUM_VERTS)
    
        print("NormalAxis1 =", axis)
        print("Main Angle (Rad)", main_angle, " > degrees", main_angle_degrees)
        print("Division Angle (Radians)", div_angle)
        print("AXIS:", axis)
    
    trig_arc_verts = []

    # optimized, instead of checking revision for each vertex in the loop.
    # means more code, but meh.
    if BUILD_REV >= CHANGE_REV:
        for i in range(NUM_VERTS):
            rotation_matrix = mathutils.Matrix.Rotation(i*-div_angle, 3, axis)
            
            trig_point = rotation_matrix * (arc_start - obj_centre - arc_centre)
            trig_point += obj_centre + arc_centre
            trig_arc_verts.append(trig_point)        
    else:    
        for i in range(NUM_VERTS):
            rotation_matrix = mathutils.Matrix.Rotation(i*-div_angle, 3, axis)
 
            trig_point = (arc_start - obj_centre - arc_centre) * rotation_matrix
            trig_point += obj_centre + arc_centre
            trig_arc_verts.append(trig_point)        
        
    return trig_arc_verts



def get_arc_from_state(points, guide_verts, mode, NUM_VERTS, context):

     # get control points and knots.
    h_control = guide_verts[0]
    radial_centre = guide_verts[1]
    knot1, knot2 = points[0], points[1]

    # draw fillet ( 2 modes )        
    if mode == 'KAPPA':
        kappa_ctrl_1 = knot1.lerp(h_control, context.scene.CurveHandle1)
        kappa_ctrl_2 = knot2.lerp(h_control, context.scene.CurveHandle2)
        arc_verts = bezlerp(knot1, kappa_ctrl_1, kappa_ctrl_2, knot2, NUM_VERTS)

    if mode == 'TRIG':
        arc_centre = radial_centre        
        arc_start = knot1
        arc_end = knot2
        arc_verts = get_correct_verts(arc_centre, arc_start, arc_end, 
                                        NUM_VERTS, context)

    return arc_verts                                        
    


''' generate the geometry already! '''


def generate_geometry_already(self, context):


    if init_functions(self, context) == None:
        return    
    
    radius_rate = bpy.context.scene.MyMove
    if radius_rate == 0.0:
        # why?
        report_string = "pick values above 0.0000"
        self.report({'INFO'}, report_string)
        return
    
    NUM_VERTS = context.scene.NumVerts
    mode = context.scene.FilletMode
    points, guide_verts = init_functions(self, context)

    
    bpy.ops.object.mode_set(mode='OBJECT')
    obj = context.object

    # not sure if this is still needed.    
    removable_vert = find_index_of_selected_vertex(obj)
    if removable_vert == None:
        # user has unselected it.
        report_string = "Atleast one vertex must be selected"
        self.report({'INFO'}, report_string)
        return

    arc_verts = get_arc_from_state(points, guide_verts, mode, NUM_VERTS, context)
    idx1, idx2 = return_connected_from_object(obj)

    # make vertices
    obj.data.vertices.add(NUM_VERTS)
    vertex_counter = NUM_VERTS
    for vert in range(len(arc_verts)):
        obj.data.vertices[-vertex_counter].co = arc_verts[vert]        
        vertex_counter -= 1
    
    # build edges, find a prettier way to do this. it's ridiculous.
    NUM_EDGES = (NUM_VERTS - 1)
    obj.data.edges.add(NUM_EDGES)

    # must count current verts first
    current_vert_count = len(bpy.context.object.data.vertices)
    edge_counter = -NUM_EDGES
    vertex_ID = current_vert_count - NUM_VERTS
    for edge in range(NUM_VERTS-1):
        a = vertex_ID
        b = vertex_ID+1
        obj.data.edges[edge_counter].vertices = [a, b]
        if DEBUG:
            print(str(edge_counter)+"[", a, ",", b, "]")

        edge_counter += 1
        vertex_ID += 1
    
    # connect first and last new edge with the 2 existing 'found indices'
    obj.data.edges.add(2)
    last_new_vert = current_vert_count-1
    first_new_vert = current_vert_count-NUM_VERTS
    obj.data.edges[-2].vertices = [idx1, first_new_vert]
    obj.data.edges[-1].vertices = [idx2, last_new_vert]
    
    # then delete 'active' vert YAY!
    # do that here. ugly code here.
    obj.data.update()
    bpy.ops.object.mode_set(mode='EDIT')

    # unselect all.
    bpy.ops.mesh.select_all(action='TOGGLE')
    
    # return to object mode to perform vertex selection
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.active_object.data.vertices[removable_vert].select = True

    # back into edit mode, delete the very first vertex again.
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.delete()
    
    # because i am lazy, this cleans up the doubles generated by a fillet
    # size that is equal to one of the edge lengths. i should be shot for this.
    if radius_rate == 1.0:
        bpy.ops.mesh.select_all(action='TOGGLE')
        bpy.ops.mesh.remove_doubles()
        bpy.ops.mesh.select_all(action='TOGGLE')
        
    return




''' director function '''



def init_functions(self, context):

    obj = context.object 
    
    # [TODO] eventually the print statements can be moved elsewhere.
    # if found_index or connected vertex are None, code should never
    # reach this point anyway.

    # Finding vertex.    
    found_index = find_index_of_selected_vertex(obj)
    if found_index != None:
        if DEBUG:
            print("you selected vertex with index", found_index)
        connected_verts = find_connected_verts(obj, found_index)
    else:
        if DEBUG:
            print("select one vertex, no more, no less")
        return None
    

    # Find connected vertices.
    if connected_verts == None:
        if DEBUG:
            print("vertex connected to only 1 other vert, or none at all")
            print("remove doubles, the script operates on vertices with 2 edges")
        return None
    else:
        if DEBUG:
            print(connected_verts)
    

    # reaching this stage means the vertex has 2 connected vertices. good.
    # Find distances and maximum radius.
    distances = find_distances(obj, connected_verts, found_index)

    if DEBUG:
        for d in distances:
            print("from", found_index, "to", d[0], "=", d[1])
    
    max_rad = min(distances[0][1],distances[1][1])
    if DEBUG:    
        print("max radius", max_rad)

    return generate_fillet(obj, connected_verts, max_rad, found_index)




''' GL drawing '''


# slightly ugly use of the string representation of GL_LINE_TYPE.
def draw_polyline_from_coordinates(context, points, LINE_TYPE):
    region = context.region
    rv3d = context.space_data.region_3d

    bgl.glColor4f(1.0, 1.0, 1.0, 1.0)

    if LINE_TYPE == "GL_LINE_STIPPLE":
        bgl.glLineStipple(4, 0x5555)
        bgl.glEnable(bgl.GL_LINE_STIPPLE)
        bgl.glColor4f(0.3, 0.3, 0.3, 1.0)
    
    bgl.glBegin(bgl.GL_LINE_STRIP)
    for coord in points:
        vector3d = (coord.x, coord.y, coord.z)
        vector2d = loc3d2d(region, rv3d, vector3d)
        bgl.glVertex2f(*vector2d)
    bgl.glEnd()
    
    if LINE_TYPE == "GL_LINE_STIPPLE":
        bgl.glDisable(bgl.GL_LINE_STIPPLE)
        bgl.glEnable(bgl.GL_BLEND)  # back to uninterupted lines
    
    return



def draw_points(context, points, size, gl_col):
    region = context.region
    rv3d = context.space_data.region_3d
    
    
    bgl.glEnable(bgl.GL_POINT_SMOOTH)
    bgl.glPointSize(size)
    bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
    
    bgl.glBegin(bgl.GL_POINTS)
    bgl.glColor4f(*gl_col)    
    for coord in points:
        vector3d = (coord.x, coord.y, coord.z)
        vector2d = loc3d2d(region, rv3d, vector3d)
        bgl.glVertex2f(*vector2d)
    bgl.glEnd()
    
    bgl.glDisable(bgl.GL_POINT_SMOOTH)
    bgl.glDisable(bgl.GL_POINTS)
    return



def draw_text(context, location, NUM_VERTS):

    bgl.glColor4f(1.0, 1.0, 1.0, 0.8)
    xpos, ypos = location
    font_id = 0
    blf.size(font_id, 12, 72)  #fine tune
    blf.position(font_id, location[0], location[1], 0)
    
    num_edges = str(NUM_VERTS - 1)
    if num_edges == str(1):
        postfix = " edge"
    else:
        postfix = " edges"
    
    display_text = str(NUM_VERTS)+" vert fillet, " + num_edges + postfix
    blf.draw(font_id, display_text)
    return
    
    
   
def draw_callback_px(self, context):
    
    if init_functions(self, context) == None:
        return
        
    region = context.region
    rv3d = context.space_data.region_3d
    points, guide_verts = init_functions(self, context)
    
    NUM_VERTS = context.scene.NumVerts
    mode = context.scene.FilletMode
    arc_verts = get_arc_from_state(points, guide_verts, mode, NUM_VERTS, context)

    # draw bevel, followed by symmetry line, then fillet edge loop
    draw_polyline_from_coordinates(context, points, "GL_LINE_STIPPLE")
    draw_polyline_from_coordinates(context, guide_verts, "GL_LINE_STIPPLE")
    draw_polyline_from_coordinates(context, arc_verts, "GL_BLEND")

    # draw arc verts, then radial centre   
    if DRAW_POINTS:
        draw_points(context, arc_verts, 4.2, gl_col1)    
        draw_points(context, [guide_verts[1]], 5.2, gl_col2)
    
    # draw bottom left, above object name the number of vertices in the fillet
    draw_text(context, (65, 30), NUM_VERTS)
        
    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)
    return


    
''' UI elements '''



class UIPanel(bpy.types.Panel):
    bl_label = "Dynamic Edge Fillet"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOL_PROPS"
 
    scn = bpy.types.Scene
    object = bpy.context.object
    
    scn.MeshVertexIndex = bpy.props.IntProperty(min=0, default=0)
    
    scn.FilletMode = bpy.props.EnumProperty( items =(
                                                ('TRIG', 'TRIG', ''),
                                                ('KAPPA', 'KAPPA', '')),
                                            name = 'filletmodes',
                                            default = 'TRIG' )
    
    scn.MyMove = bpy.props.FloatProperty(min=0.0, max=1.0, 
                                            default=0.5, precision=5,
                                            name="ratio of shortest edge")
    
    scn.NumVerts = bpy.props.IntProperty(min=2, max=64, default=12,
                                            name="number of verts")
    
    scn.CurveHandle1 = bpy.props.FloatProperty( min=0.0, max=4.0, 
                                                default = KAPPA,
                                                name="handle1")
    scn.CurveHandle2 = bpy.props.FloatProperty( min=0.0, max=4.0, 
                                                default = KAPPA,
                                                name="handle2")
    
    # figuring out how to prevent it from redrawing, when check_vertex pressed
    # scn.FILLET_DRAWING = bpy.props.BoolProperty(default=False)
    
    
    @classmethod
    def poll(self, context):
        
        obj = context.object
        
        found_index = find_index_of_selected_vertex(obj)
        if found_index != None:
            connected_verts = find_connected_verts(obj, found_index)
            if connected_verts != None:
                if context.object.mode == 'EDIT':   
                    return True
        
    
    def draw(self, context):
        layout = self.layout
        ob = context.object
        scn = context.scene

        row1 = layout.row(align=True)
        row1.prop(scn, "FilletMode", expand = True)

        row2 = layout.row(align=True)
        row2.operator("dynamic.fillet")

        row3 = layout.row(align=True)
        row3.prop(scn, "MyMove", slider=True)

        if scn.FilletMode == 'KAPPA':
            row4 = layout.row(align=True)
            row4.prop(scn, "CurveHandle1", slider=True)
            row4.prop(scn, "CurveHandle2", slider=True)

            row5 = layout.row(align=True)
            row5.operator("reset.handles")



class OBJECT_OT_reset_handles(bpy.types.Operator):
    bl_idname = "reset.handles"
    bl_label = "Reset Handles"
    bl_description = "Resets both handles, a convenience"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        KAPPA = 4 * (( math.sqrt(2) - 1) / 3 )        
        context.scene.CurveHandle1 = KAPPA
        context.scene.CurveHandle2 = KAPPA
        return {'FINISHED'}



class OBJECT_OT_draw_fillet(bpy.types.Operator):
    bl_idname = "dynamic.fillet"
    bl_label = "Check Vertex"
    bl_description = "Allows the user to dynamically fillet a vert/edge"
    bl_options = {'REGISTER', 'UNDO'}
    
    # i understand that a lot of these ifs are redundant, scheduled for
    # deletion. is 'RELEASE' redundant for keys?
   
    def modal(self, context, event):
        context.area.tag_redraw()
        
        if event.type == 'ESC':
            if event.value == 'RELEASE':
                # print("discontinue drawing")
                context.area.tag_redraw()
                context.region.callback_remove(self._handle)
                return {'CANCELLED'}

        
        if event.type == 'RIGHTMOUSE':
            if event.value == 'RELEASE':
                # update on alternate vertex selection.
                bpy.ops.object.editmode_toggle()
                bpy.ops.object.editmode_toggle()
                return {'PASS_THROUGH'}

        
        if event.type == 'LEFTMOUSE':
            if event.value in ('PRESS', 'RELEASE'):
                context.area.tag_redraw()
                # HALF_RAD = context.scene.MyMove
                # context.region.callback_remove(self._handle)                
                return {'PASS_THROUGH'}

        if event.shift:
            # take control of numpad plus / minus        
            if event.type == 'NUMPAD_PLUS' and event.value == 'RELEASE':
                if context.scene.NumVerts <= 64:
                    context.scene.NumVerts += 1
                return {'PASS_THROUGH'} 
    
    
            if event.type == 'NUMPAD_MINUS' and event.value == 'RELEASE':
                if context.scene.NumVerts >=3:
                    context.scene.NumVerts -= 1
                return {'PASS_THROUGH'} 
    

        
        # allows you to rotate around.        
        if event.type == 'MIDDLEMOUSE':
            # context.area.tag_redraw()
            # print(event.value) 
            if event.value == 'PRESS':
                # print("Allow to rotate")
                context.area.tag_redraw()
                return {'PASS_THROUGH'}           
            if event.value == 'RELEASE':
                context.area.tag_redraw()
                # print("allow to interact with ui")
                return {'PASS_THROUGH'}
        
        # allows you to zoom.
        if event.type in ('WHEELUPMOUSE', 'WHEELDOWNMOUSE'):
            context.area.tag_redraw()
            return {'PASS_THROUGH'} 
        
        # make real
        if event.type in ('RET','NUMPAD_ENTER') and event.value == 'RELEASE':
            # print("Make geometry")
            generate_geometry_already(self, context)
            context.region.callback_remove(self._handle)            
            return {'CANCELLED'}     
                        
            
        # context.area.tag_redraw()
        return {'PASS_THROUGH'}
    
    
    
    def invoke(self, context, event):

        # let's make sure we have the right vertex. UGLY!        
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()

        if context.area.type == 'VIEW_3D':
            context.area.tag_redraw()
            context.window_manager.modal_handler_add(self)
                    
            # Add the region OpenGL drawing callback
            # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
            self._handle = context.region.callback_add(
                            draw_callback_px, 
                            (self, context), 
                            'POST_PIXEL')

            
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, 
            "View3D not found, cannot run operator")
            context.area.tag_redraw()            
            return {'CANCELLED'}
    
    
 
bpy.utils.register_module(__name__)