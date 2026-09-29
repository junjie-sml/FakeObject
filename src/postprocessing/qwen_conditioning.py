"""Image references for Qwen, whose pipeline has no native mask_image input."""
def mask_references(image,mask,prompt):
    """Keep image order and the model's required <imageN> references in sync."""
    image=image.convert('RGB')
    mask=mask.convert('L')
    if mask.size!=image.size: raise ValueError('Mask and image dimensions must match.')
    if mask.getbbox() is None: raise ValueError('Selected mask is empty.')
    instruction=('Edit <image1>. <image2> is a localization mask for <image1>: white marks the ENTIRE selected target, '
                 'black must stay unchanged. Apply the user-requested transformation throughout the white region. '
                 'Output the edited photograph, without rendering the mask. '+prompt)
    return [image,mask.convert('RGB')],instruction
