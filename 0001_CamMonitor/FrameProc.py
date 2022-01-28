import cv2
import numpy as np

def IsDiff(frame1, frame2, thresh=50) -> bool:
    """
    @description  : judge two frames same?
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    tep = abs(frame1-frame2)
    mtep=np.max(tep)
    return mtep>thresh
    
    