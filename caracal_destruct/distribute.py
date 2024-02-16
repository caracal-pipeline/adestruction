class DistributionException(Exception):
    pass

class Scatter():
    def __init__(self, pipeline, config=None, obsidx=0, spwid=0):
        self.pipeline = pipeline
        self.obsidx = obsidx
        self.spwid = spwid
        self.config = config

    def set(self, nband=None, bands=None):
        self.nchan = self.pipeline.nchans[self.obsidx][self.spwid]
        runsdict = self.config.runs

        if nband:
            wsize = self.nchan//nband
            
            bw_edges = range(0, self.nchan, wsize)
            self.bands = [f"{self.spwid}:{band}~{band+wsize}"for band in bw_edges]
            self.nband = nband
        else:
            self.nband = len(bands)
            self.bands = bands

        self.runsdict = runsdict or self.runsdict or {}

        self.runs = [None]*self.nband
        for bandrun in self.runsdict:
            thisrun = {}
            # add common opts
            thisrun.update(self.config.get("all", {}))
            # add imports
            for imp in bandrun.get("import", []):
                thisrun.update(runsdict[imp].options)
            # add fron this run
            thisrun.update(bandrun.options)
                
            optlist =  []
            for key,val in thisrun.items():
                if isinstance(val, bool):
                    val = str(val).lower()
                optlist.append(f"--{key} {val}")
            self.runs[ bandrun["index"] ] = optlist
