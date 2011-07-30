import bpy
import bgl
import mathutils
import bpy_extras
import math

from mathutils import Vector
from mathutils.geometry import interpolate_bezier as bezlerp
from bpy_extras.view3d_utils import location_3d_to_region_2d as loc3d2d

# OBJECTIVE

# fillet the selected vertex of a profile by dragging the mouse inwards
# the max fillet radius is reached at the shortest delta of surrounding verts.


# [x] MILESTONE 1 
# [x] get selected vertex index. 
# [x] get indices of attached verts.
# [x] get their lengths, return shortest.
# [x] shortest length is max fillet radius.

# [x] MILESTONE 2
# [x] draw gl bevel line from both edges (bev_edge1, bev_edge2)
# [x] find center of bevel line
# [x] draw line of radius length from found_index through center of bevel line.
# [x] call new found point 'fillet_centre"
# [x] draw pline from bev_edge1 to 2, with delta from fillet_centre (kappa)
# [x] draw pline from bev_edge1 to 2, with delta from fillet_centre (trig_lazy)
# [x] draw pline from bev_edge1 to 2, with delta from fillet_centre (trig)

# [ ] MILESTONE 3
# [x] draw faux vertices
# [x] draw opengl filleted line.
# [ ] make shift+rightlick, draw a line from selected vertex to mouse cursor.
# [ ] allow mouse wheel to define segment numbers.
# [ ] enter to accept, and make real. esc to cancel.
# [ ] warn user to apply all visual transforms, before running script


# ============================================================================

''' temporary constants '''

NUM_SEGS = 15
NUM_VERTS = NUM_SEGS + 1
HALF_RAD = 0.5
KAPPA = 4 * (( math.sqrt(2) - 1) / 3 )
DEBUG = True


''' switches '''

modes = ('TRIG_LAZY','KAPPA', 'TRIG')
mode = modes[2]
DRAW_POINTS = True



''' helper functions '''


def find_index_of_selected_vertex(obj):

    # force 'OBJECT' mode temporarily. [TODO]
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
    distance_from_f = max_rad * HALF_RAD

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



def resposition_arc_points(arc_verts, radial_centre):
    # ensure that every arc point is indeed radial distance away from center.
    revised_arc_points = []

    radial_dist_first = (arc_verts[0]-radial_centre).length
    radial_dist_last = (arc_verts[-1]-radial_centre).length
    desired_radial_distance = (radial_dist_first + radial_dist_last) * 0.5

    for point in arc_verts:
        radial_distance = (point-radial_centre).length
        ratio = 1/(radial_distance / desired_radial_distance)
        new_location = radial_centre.lerp(point, ratio)
        new_distance = (radial_centre-new_location).length
        revised_arc_points.append(new_location)
        print("was", radial_distance, "becomes", new_distance)

    return revised_arc_points


def get_correct_verts(arc_centre, arc_start, arc_end, NUM_VERTS, context):
        
    obj_centre = context.object.location
    axis = mathutils.geometry.normal(arc_centre, arc_end, arc_start)
 
    point1 = arc_start - arc_centre
    point2 = arc_end - arc_centre
    main_angle = point1.angle(point2)
    main_angle_degrees = math.degrees(main_angle)

    div_angle = main_angle / (NUM_VERTS - 1)

    if DEBUG == True:
        print("arc_centre =", arc_centre)
        print("arc_start =", arc_start)
        print("arc_end =", arc_end)
        print("NUM_VERTS =", NUM_VERTS)
    
        print("NormalAxis1 =", axis)
        print("Main Angle (Rad)", main_angle, " > degrees", main_angle_degrees)
        print("Division Angle (Radians)", div_angle)
        print("AXIS:", axis)
    
    trig_arc_verts = []

    for i in range(NUM_VERTS):
        rotation_matrix = mathutils.Matrix.Rotation(i*-div_angle, 3, axis)
        trig_point = (arc_start - obj_centre - arc_centre) * rotation_matrix
        trig_point += obj_centre + arc_centre
        trig_arc_verts.append(trig_point)        
        
    return trig_arc_verts





''' director function '''



def init_functions(self, context):

    obj = context.object 

    # Finding vertex.    
    found_index = find_index_of_selected_vertex(obj)
    if found_index != None:
        print("you selected vertex with index", found_index)
        connected_verts = find_connected_verts(obj, found_index)
    else:
        print("select one vertex, no more, no less")
        return
    

    # Find connected vertices.
    if connected_verts == None:
        print("vertex connected to only 1 other vert, or none at all")
        print("remove doubles, the script operates on vertices with 2 edges")
        return
    else:
        print(connected_verts)
    

    # reaching this stage means the vertex has 2 connected vertices. good.
    # Find distances and maximum radius.
    distances = find_distances(obj, connected_verts, found_index)
    for d in distances:
        print("from", found_index, "to", d[0], "=", d[1])

    max_rad = min(distances[0][1],distances[1][1])
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
    # bgl.glEnable(bgl.GL_BLEND)
    bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
    
    bgl.glBegin(bgl.GL_POINTS)
    # draw red
    bgl.glColor4f(*gl_col)    
    for coord in points:
        vector3d = (coord.x, coord.y, coord.z)
        vector2d = loc3d2d(region, rv3d, vector3d)
        bgl.glVertex2f(*vector2d)
    bgl.glEnd()
    
    bgl.glDisable(bgl.GL_POINT_SMOOTH)
    bgl.glDisable(bgl.GL_POINTS)
    return


    
def draw_callback_px(self, context):
    
    objlist = context.selected_objects
    names_of_empties = [i.name for i in objlist]

    region = context.region
    rv3d = context.space_data.region_3d
    points, guide_verts = init_functions(self, context)
    
    # draw bevel
    draw_polyline_from_coordinates(context, points, "GL_LINE_STIPPLE")
    
    # draw symmetry line
    draw_polyline_from_coordinates(context, guide_verts, "GL_LINE_STIPPLE")
    
    # get control points and knots.
    h_control = guide_verts[0]
    radial_centre = guide_verts[1]
    knot1, knot2 = points[0], points[1]

    kappa_ctrl_1 = knot1.lerp(h_control, KAPPA)
    kappa_ctrl_2 = knot2.lerp(h_control, KAPPA)
    arc_verts = bezlerp(knot1, kappa_ctrl_1, kappa_ctrl_2, knot2, NUM_VERTS)

    # draw fillet ( 2 modes )        

    if mode == 'TRIG_LAZY':
        arc_verts = resposition_arc_points(arc_verts, radial_centre)
    
    if mode == 'KAPPA':
        print("using vanilla kappa, this mode produces a poor approximation")
    
    if mode == 'TRIG':
        arc_centre = radial_centre        
        arc_start = knot1
        arc_end = knot2
        arc_verts = get_correct_verts(arc_centre, 
                        arc_start, 
                        arc_end, 
                        NUM_VERTS, 
                        context)
        # get_correct_verts(arc_centre, arc_start, arc_end, NUM_VERTS, context)
        
    draw_polyline_from_coordinates(context, arc_verts, "GL_BLEND")
    
    gl_col1 = 1.0, 0.2, 0.2, 1.0  # vertex arc color
    gl_col2 = 0.5, 0.7, 0.4, 1.0  # radial center color
    
    if DRAW_POINTS == True:
        draw_points(context, arc_verts, 4.2, gl_col1)    
        draw_points(context, [radial_centre], 5.2, gl_col2)
        
    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)
    return


    
''' UI elements '''



class UIPanel(bpy.types.Panel):
    bl_label = "Dynamic Edge Fillet"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
 
    scn = bpy.types.Scene
    object = bpy.context.object
    # scn.Monster = object.location.x
    # scn.MyMove = bpy.props.FloatProperty()

     
    def draw(self, context):
        layout = self.layout
        ob = context.object
        scn = context.scene

        row1 = layout.row(align=True)
        # row1.prop(ob, "location")
        row1.operator("dynamic.fillet")
        # row1.prop(ob, 'location', index = 0, slider = True)




class OBJECT_OT_add_object(bpy.types.Operator):
    bl_idname = "dynamic.fillet"
    bl_label = "Check Vertice"
    bl_description = "Allows the user to dynamically fillet a vert/edge"
    bl_options = {'REGISTER', 'UNDO'}

    '''
    scale = FloatVectorProperty(name='scale',
                                default=(1.0, 1.0, 1.0),
                                subtype='TRANSLATION',
                                description='scaling')
    '''
    
    
    def modal(self, context, event):
        context.area.tag_redraw()
        
        if event.type == 'RIGHTMOUSE':
            if event.value == 'RELEASE':
                print("discontinue drawing")
                context.area.tag_redraw()
                context.region.callback_remove(self._handle)
                return {'CANCELLED'}  
        
        # context.area.tag_redraw()
        return {'RUNNING_MODAL'}
    
    
    
    def invoke(self, context, event):

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
    
    
    '''    
    
    def execute(self, context):

        #add_object(self, context)
        init_functions(self, context)

        return {'FINISHED'}

    '''


 
bpy.utils.register_module(__name__)