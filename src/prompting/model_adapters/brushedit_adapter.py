def compile_brushedit(spec):
    f = spec.fictional_object
    # Native BrushEdit consumes a target-region caption, not an instruction paragraph.
    return (f'Photo of an unfamiliar manufactured object, {f.primary_geometry}, '+
            f.secondary_structure[0]+', '+', '.join(f.materials)+' in '+', '.join(f.colors)+
            ', subtle seams, realistic light and contact shadow.')
