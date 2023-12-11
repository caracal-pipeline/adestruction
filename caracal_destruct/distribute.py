import numpy as np

class DistributionException(Exception):
    pass

class Scatter():
    def __init__(self, pipeline, runsdict=None, obsidx=0, spwid=0):
        self.pipeline = pipeline
        self.obsidx = obsidx
        self.spwid = spwid
        self.runsdict = runsdict

    def set(self, nband=None, bands=None, runsdict=None):
        self.nchan = self.pipeline.nchans[self.obsidx][self.spwid]

        if nband:
            wsize = self.nchan//nband
            
            bw_edges = np.arange(0, self.nchan, wsize, dtype=int)
            self.bands = [f"{self.spwid}:{band}~{band+wsize}"for band in bw_edges]
            self.nband = nband
        else:
            self.nband = len(bands)
            self.bands = bands

        
        self.runsdict = runsdict or self.runsdict or {}

        self.runs = [None]*self.nband
        for bandrun in self.runsdict:
            optlist =  []
            for key,val in bandrun["options"].items():
                if isinstance(val, bool):
                    val = str(val).lower()
                optlist.append(f"--{key} {val}")
            self.runs[ bandrun["index"] ] = optlist

            
