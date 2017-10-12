from math import sqrt

figureNo = 1
LNCS_COLUMN_WIDTH = 347.12354

class Plot(object):
    """
    on a Plot object, call any pylab function to add a plot
    and legend() to add your legend
    """
    
    def __init__(self, name = "Plot", LaTeX = False, **kwargs):
        global figureNo
        self.fapps = []
        self.name = name
        self.latex = LaTeX
        self.figureNo = figureNo
        figureNo += 1
        
        # LaTeX specific formatting settings
        # - figure dimensions (pt)
        col_width = 600.0 # column width (in pt) - get this from LaTeX using \showthe\columnwidth
        self.fig_width_pt = col_width/2
        self.aspect_ratio =  (sqrt(5)-1.0)/2.0 # aesthetic ratio
        self.fig_height_pt = None # None = determined by aspect ratio
        # - fonts
        self.font_family = 'serif'
        self.tick_font_size = 7
        self.label_font_size = 7
        # - axes and borders
        self.tick_extend_into_right_border_chars = 2 # rightmost x-axis tick label may extend into border - this is the number of characters that extend into the border
        self.left_tick_label_chars = 4 # the number of characters used in the y-axis labels (must make sure there's room for these labels in the border)
        self.border = 0.05 # fraction of space that is to be taken up by borders around the figure
        self.latex_preamble = None
        self.drawn = False
        
        self.__dict__.update(kwargs)
    
    def apply(self, function, *args, **kwargs):
        self.fapps.append((function, args, kwargs))
        
    def __getattr__(self, name):
        return lambda *x, **y: self.apply(name, *x, **y)
    
    def draw(self):
        #import matplotlib.pyplot as pylab
        import pylab
        
        # make some latex-specific settings for drawing
        if self.latex:
            # set general parameters for the generation of figures for print
            inches_per_pt = 1.0/72.27
            aspect_ratio = self.aspect_ratio
            fig_width_pt = self.fig_width_pt
            fig_height_pt = self.fig_height_pt
            if fig_height_pt is None:
                fig_height_pt = fig_width_pt*aspect_ratio
            fig_width = fig_width_pt*inches_per_pt # width in inches
            fig_height = fig_height_pt*inches_per_pt # height in inches
            fig_size = [fig_width,fig_height]
            tick_font_size = self.tick_font_size
            label_font_size = self.label_font_size
            params = {'backend': 'ps',
                      'axes.labelsize': label_font_size,
                      'text.fontsize': tick_font_size,
                      'legend.fontsize': tick_font_size,
                      'xtick.labelsize': tick_font_size,
                      'ytick.labelsize': tick_font_size,
                      'text.usetex': True,
                      'figure.figsize': fig_size,
                      'font.family': self.font_family}
            if self.latex_preamble is not None:
                params["text.latex.preamble"] = self.latex_preamble
            pylab.rcParams.update(params)            

            # configure axes position
            # - compute borders (normalized to [0;1])
            border = self.border
            tick_font_width = 0.75 * tick_font_size
            yaxis_tick_width = self.left_tick_label_chars * tick_font_width / fig_width_pt # tick labels
            yaxis_label_width = float(label_font_size) / fig_width_pt # axis label (font is rotated 90 degrees, so height=size applies)
            left = border + yaxis_tick_width + yaxis_label_width
            xaxis_label_height = label_font_size * 1.4 / fig_height_pt
            xaxis_tick_height = tick_font_size * 1.4 / fig_height_pt
            bottom = border + xaxis_tick_height + xaxis_label_height
            right = border + self.tick_extend_into_right_border_chars * tick_font_width / fig_width_pt
            top = border + tick_font_size * 0.5 / fig_height_pt # (half a character always extends into the top border)
            # - compute actual graph dimensions (relative to total dimensions of figure)
            width = 1.0 - left - right
            height = 1.0 - top - bottom        

        # apply the plot
        pylab.figure(self.figureNo)
        pylab.clf()
        if self.latex:
            pylab.axes([left,bottom,width,height])            
        for fname, args, kwargs in self.fapps:
            function = eval("pylab.%s" % fname)
            function(*args, **kwargs)
        if self.latex:
            filename = "%s.pdf" % self.name
            print("saving %s" % filename)
            pylab.savefig(filename)
        else:
            pylab.draw()
    
    def plotFunction(self, f, x_start, x_end, steps, **kwargs):
        from pylab import np
        x = np.linspace(x_start, x_end, steps)
        self.plot(x, f(x), **kwargs)
    
    def show(self):
        if not self.drawn: self.draw()
        import pylab
        pylab.show()
    
def showPlots():
    import pylab
    pylab.show()   
    
# example plots
if __name__ == '__main__':
    
    # drawing multiple plots (non-blocking)
    plot = Plot("test", LaTeX=False)
    plot.plotFunction(lambda x: x*x, -5, 5, 50)
    plot.draw()
    plot2 = Plot("test2", LaTeX=False)
    plot2.plotFunction(lambda x: 2*x, -5, 5, 50)
    plot2.draw()
    showPlots()
    
    # showing multiple plots one after the other
    plot = Plot("test", LaTeX=False)
    plot.plotFunction(lambda x: x*x, -5, 5, 50)
    plot.show()
    plot2 = Plot("test2", LaTeX=False)
    plot2.plotFunction(lambda x: 2*x, -5, 5, 50)
    plot2.show()
    