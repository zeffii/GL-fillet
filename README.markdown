![GL-fillet](https://github.com/zeffii/GL-fillet/raw/master/opengl_blender_overlay_drawing.png)

    Usage  
    - Install or run the script from Text Editor  
    - Select one vertex on the corner of two connected edges  
    - go to object mode to let the script know what vertex you want to operate on  
    - back into editmode, hit Check Vertex. The fillet should start drawing  
    - adjust the settings to satisfy  
    - hold shift and press numpad_plus / numpad_minus to adjust the segments  
    - hit Enter to apply the fillet, or Esc to stop drawing.


Objective  
fillet the selected vertex of a profile.
the max fillet radius is reached at the shortest delta of surrounding verts.  
  
warning. using `"ctrl+numpad +/-"` to change the current selection of vertices will result in no changes. no fillet.  
  
Milestone 1  
[x] get selected vertex index.  
[x] get indices of attached verts.  
[x] get their lengths, return shortest.  
[x] shortest length is max fillet radius.  
  
Milestone 2  
[x] draw gl bevel line from both edges (bev_edge1, bev_edge2)  
[x] find center of bevel line  
[x] draw centre guide line.  
[x] call new found point 'fillet_centre"  
[x] calculate verts `"KAPPA"`  
[x] calculate verts `"TRIG"`  
  
Milestone 3  
[x] draw faux vertices  
[x] draw opengl filleted line.  
[x] allow view rotate, zoom  
[x] allow `"shift+numpad +/-"` to define segment numbers.  
[x] `"esc/rclick"` to cancel.  
[x] sliders update in realtime  
[x] `"enter to accept"`, and make real.  
[x] checks revision, uses code according to your blender release.  
[x] cleanup  
[x] create negative / positive switch.  
[ ] make shift+rightlick, draw manipulation line to mouse cursor.  
[ ] make faces tri, quad (quad option only available with appropriate num_verts)  
[ ] user must apply all transforms, or matrix * vector  (this i don't understand yet)