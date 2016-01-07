# dont use this  code - it is terrible :)

import bpy
import bgl
import blf
import bmesh
from mathutils import Vector

tinycad_dict = {}


def get_bevel_geometry(obj, spline, index):
    print(index)
    points = spline.points
    p1, p2, p3 = points[index - 1:index + 2]
    return [p1.co.xyz, p2.co.xyz, p3.co.xyz]


def pydata_from_bmesh(bm):
    v = [v.co[:] for v in bm.verts]
    e = [[i.index for i in e.verts] for e in bm.edges[:]]
    return v, e


def make_bm(points):
    p1, p2, p3 = points
    bm = bmesh.new()
    v1 = bm.verts.new(p1)
    v2 = bm.verts.new(p2)
    v3 = bm.verts.new(p3)
    e1 = bm.edges.new([v1, v2])
    e2 = bm.edges.new([v2, v3])
    bm.verts.index_update()
    bm.edges.index_update()
    return bm


def make_bevel(bm, self):
    
    bmesh.ops.bevel(
        bm,
        geom=[v for v in bm.verts if v.index == 1],
        offset=self.radius,
        offset_type=0,
        segments=self.segments,
        vertex_only=True,
        profile=self.profile,
        material=0,
        loop_slide=self.loop_slide,  # True,
        clamp_overlap=self.clamp_overlap  # True
    )

    verts, edges = pydata_from_bmesh(bm)
    print(len(verts))
    bm.free()
    return [verts, edges]


def smart_bevel(context):

    obj = context.active_object
    spline = obj.data.splines.active

    if not (spline.type in {'NURBS', 'POLY'}):
        print('convert to nurbs or poly first')
        return

    points = obj.data.splines.active.points
    part = [True for i in points]
    points.foreach_get("select", part)

    if not (part.count(True) == 1):
        print('pick only one point')
        return

    if (part[0] == True) or (part[-1] == True):
        print("don't pick 1st or last points to bevel")
        return

    print('>')
    idx = part.index(True)
    return get_bevel_geometry(obj, spline, idx)


def draw_func(self, context):

    if tinycad_dict['bevel'] and (len(tinycad_dict['bevel']) == 2):
        verts = tinycad_dict['bevel'][0]
        edges = tinycad_dict['bevel'][1]
    else:
        return

    # 50% alpha, 2 pixel width line
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 0.5)
    bgl.glLineWidth(2)

    # 3d lines
    bgl.glBegin(bgl.GL_LINES)
    for keys in edges:
        for k in keys:
            coordinate = verts[k]
            bgl.glVertex3f(*coordinate)
    bgl.glEnd()

    # 3d points
    vsize = 5
    bgl.glEnable(bgl.GL_POINT_SIZE)
    bgl.glEnable(bgl.GL_POINT_SMOOTH)
    bgl.glHint(bgl.GL_POINT_SMOOTH_HINT, bgl.GL_NICEST)
    bgl.glPointSize(vsize)    
    bgl.glColor3f(1.0, 0.6, 0.3)
    bgl.glBegin(bgl.GL_POINTS)
    for x, y, z in verts:
        bgl.glVertex3f(x, y, z)
    bgl.glEnd()    

    bgl.glDisable(bgl.GL_POINT_SIZE)
    bgl.glDisable(bgl.GL_POINT_SMOOTH)


    # restore opengl defaults
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)


class TCCurveBevel(bpy.types.Operator):
    """bevel a curve"""
    bl_idname = "tinycad.curve_bevel"
    bl_label = "Bevel a curve"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'    
    bl_options = {'REGISTER', 'UNDO'}

    radius = bpy.props.FloatProperty(default=0.4, min=0.0)
    segments = bpy.props.IntProperty(default=7, min=1)
    profile = bpy.props.FloatProperty(min=0.0, default=0.5, max=1.0)
    loop_slide = bpy.props.BoolProperty(default=True)
    clamp_overlap = bpy.props.BoolProperty(default=True)
    
    pos_x = bpy.props.IntProperty()
    pos_y = bpy.props.IntProperty()
    dist = bpy.props.FloatProperty()
    
    mouse_x = bpy.props.IntProperty()
    mouse_y = bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def modal(self, context, event):

        self.dist = (Vector((self.pos_x, self.pos_y, 0)) - Vector((event.mouse_x, event.mouse_y, 0))).length
        self.radius = self.dist / 100


        if tinycad_dict['points']:
            bm = make_bm(tinycad_dict['points'])
            tinycad_dict['bevel'] = make_bevel(bm, self)
 
        context.area.tag_redraw()

        if event.type == 'RET':
            print('make mesh!')
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'FINISHED'}

        elif event.type in {'ESC'}:
            print('ending drawing!')
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'CANCELLED'}

        elif event.type in {"WHEELUPMOUSE", "WHEELDOWNMOUSE", "MIDDLEMOUSE", "F6", "LEFTMOUSE", "T", "N"}:
            # val = {"WHEELUPMOUSE": 1, "WHEELDOWNMOUSE": -1}.get(event.type)
            # self.segments += val
            return {'PASS_THROUGH'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            args = (self, context)
            draw_handler_add = bpy.types.SpaceView3D.draw_handler_add
            self._handle = draw_handler_add(draw_func, args, 'WINDOW', 'POST_VIEW')

            tinycad_dict['points'] = smart_bevel(context)
            tinycad_dict['bevel'] = []

            context.window_manager.modal_handler_add(self)
            
            self.pos_x = event.mouse_x
            self.pos_y = event.mouse_y
            self.mouse_x = event.mouse_x
            self.mouse_y = event.mouse_y

            
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}


def register():
    bpy.utils.register_class(TCCurveBevel)


def unregister():
    bpy.utils.unregister_class(TCCurveBevel)


if __name__ == "__main__":
    register()
