import numpy as np

class DistributionException(Exception):
    pass

class Scatter():
    def __init__(self, pipeline, obsidx=0):
        self.pipeline = pipeline
        self.obsidx = obsidx

    def set(self, bands):
        self.nchan = self.pipeline.nchans[self.obsidx]
        if isinstance(bands, int):
            wsize = self.nchan/bands
            
            bw_edges = np.arange(0, self.nchan, wsize)
            bands = [f"{band}~{band+wsize}"for band in bw_edges]

        elif hasattr(bands, "__iter__") and not isinstance(bands, (bytes, str)):
            # We have a list/tuple
            pass
        else:
            raise DistributionException(
                f"Cannot distribute pipeline over {bands}. Please verify that this is a list of strings (CASA style)")

        self.bands = bands
