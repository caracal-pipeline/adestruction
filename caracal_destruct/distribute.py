import numpy as np

class DistributionException(Exception):
    pass

class Scatter():
    def __init__(self, pipeline, runsdict=None, obsidx=0, spwid=0):
        self.pipeline = pipeline
        self.obsidx = obsidx
        self.spwid = spwid
        self.runsdict = runsdict

    def set(self, bands, runsdict=None):
        self.nchan = self.pipeline.nchans[self.obsidx][self.spwid]
        if isinstance(bands, int):
            wsize = self.nchan//bands
            
            bw_edges = np.arange(0, self.nchan, wsize, dtype=int)
            bands = [f"{self.spwid}:{band}~{band+wsize}"for band in bw_edges]

        elif hasattr(bands, "__iter__") and not isinstance(bands, (bytes, str)):
            # We have a list/tuple
            pass
        else:
            raise DistributionException(
                f"Cannot distribute pipeline over {bands}. Please verify that this is a list of strings (CASA style)")


        self.bands = bands
        self.nbands = len(bands)
        self.runsdict = runsdict or self.runsdict or {}

        self.runs = [None]*self.nbands
        for bandrun in runsdict:
            optlist = [f"--{key} {val}" for key,val in bandrun.options.items()]
            self.runs[bandrun.index] = optlist

            
