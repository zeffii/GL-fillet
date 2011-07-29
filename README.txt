# OBJECTIVE

# fillet the selected vertex of a profile by dragging the mouse inwards
# the max fillet radius is reached at the shortest delta of surrounding verts.

# [x] MILESTONE 1 
# [x] get selected vertex index. 
# [x] get indices of attached verts.
# [x] get their lengths, return shortest.
# [x] shortest length is max fillet radius.
#
# [x] MILESTONE 2
# [x] draw gl bevel line from both edges (bev_edge1, bev_edge2)
# [x] find center of bevel line
# [x] draw centre guide line.
# [x] call new found point 'fillet_centre"
# [x] calculate verts 'KAPPA'
# [x] calculate verts 'TRIG'
#
# [ ] MILESTONE 3
# [x] draw faux vertices
# [x] draw opengl filleted line.
# [x] allow view rotate, zoom
# [x] allow ctrl+numpad +/- to define segment numbers.
# [x] esc/rclick to cancel.
# [x] sliders update in realtime
# [x] enter to accept, and make real.
# [ ] make shift+rightlick, draw manipulation line to mouse cursor.
# [ ] cleanup
# [ ] make faces [ tri, quad ]
# [ ] user must apply all transforms, or matrix * vector