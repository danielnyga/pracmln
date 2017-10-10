import sys
import re
import colorsys
import math

# colors

randomVariableColor = "#B1CBDA" # (177,203,218)
decisionNodeColor = "#45CA46" # (60,202,80)

def to_rgb_color(c1, c2, c3, model):
    '''
    Converts a color given by the components c1, c2 and c3 into RGB space.
    The input color model needs to be specified by model. Inputs are floats in [0,1]. 
    Returns a triple (r, g, b)
    '''
    if model == 'rgb':
        return (c1, c2, c3)
    elif model == 'hsv':
        return colorsys.hsv_to_rgb(c1, c2, c3)
    elif model == 'hsl':
        return colorsys.hls_to_rgb(c1, c2, c3)
    else:
        raise Exception('Unknown color model: %s' % model)

def to_html_hex(c1, c2, c3, model):
    '''
    Converts the given color components of in the model model
    into an html hax color string.
    '''
    (r, g, b) = to_rgb_color(c1, c2, c3, model)
    (r, g, b) = (int(math.floor(r * 255.)), int(math.floor(g * 255.)), int(math.floor(b * 255.)))
    return '#%s%s%s' % (hex(r)[2:].ljust(2, '0'), hex(g)[2:].ljust(2, '0'), hex(b)[2:].ljust(2, '0'))

# classes

class Graph(object):
    def __init__(self):
        self.GUID = 0
        self.nodes = []
        self.edges = []
    
    def nextId(self):
        self.GUID += 1
        return self.GUID
    
    def write(self, out):
        out.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:y="http://www.yworks.com/xml/graphml" xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns http://www.yworks.com/xml/schema/graphml/1.1/ygraphml.xsd">\n')
        out.write('<key for="graphml" id="d0" yfiles.type="resources"/>\n')
        out.write('<key attr.name="url" attr.type="string" for="node" id="d1"/>\n')
        out.write('<key attr.name="description" attr.type="string" for="node" id="d2"/>\n')
        out.write('<key for="node" id="d3" yfiles.type="nodegraphics"/>\n')
        out.write('<key attr.name="Beschreibung" attr.type="string" for="graph" id="d4">\n')
        out.write('<default/>\n')
        out.write('</key>\n')
        out.write('<key attr.name="url" attr.type="string" for="edge" id="d5"/>\n')
        out.write('<key attr.name="description" attr.type="string" for="edge" id="d6"/>\n')
        out.write('<key for="edge" id="d7" yfiles.type="edgegraphics"/>\n')
        out.write('<graph edgedefault="directed" id="G">\n')
        for n in self.nodes: n.write(out)
        for e in self.edges: e.write(out)        
        out.write('</graph>\n')
        out.write('<data key="d0">\n')
        out.write('<y:Resources/>\n')
        out.write('</data>\n')
        out.write('</graphml>\n')

class Node(object):
    def __init__(self, graph, color='#dddddd', model='rgb', **kwargs):
        '''
        color may be an html color hex string in rgb space or a triple (c1, c2, c3)
        in a different color space (ci in [0,1].
        ''' 
        graph.nodes.append(self)
        self.id = graph.nextId()
        self.shape = "rectangle" # "ellipse"
        if type(color) is str:
            if not model == 'rgb': raise Exception('string colors must be in RGB space.')
            self.color = color
        else:
            self.color = to_html_hex(color[0], color[1], color[2], model)
        self.label = str(self.id)
        self.xpos = 0
        self.ypos = 0
        for key, value in kwargs.items():
            if type(value)==str:
                value = value.replace('<','').replace('>','')
            self.__setattr__(key, value)
    
    def write(self, out):
        width = max(float(len(self.label))*7,35)
        out.write('<node id="n%s">' % (self.id))
        out.write('<data key="d2"/>')
        out.write('<data key="d3">')
        out.write('<y:ShapeNode>')
        out.write('<y:Geometry height="30.0" width="%s" x="%d" y="%d"/>' % (str(width), self.xpos, self.ypos))
        out.write('<y:Fill color="%s" transparent="false"/>' % (self.color))
        out.write('<y:BorderStyle color="#000000" type="line" width="1.0"/>')
        out.write('<y:NodeLabel alignment="center" autoSizePolicy="content" fontFamily="Dialog" fontSize="12" fontStyle="plain" hasBackgroundColor="false" hasLineColor="false" height="18.701171875" modelName="internal" modelPosition="c" textColor="#000000" visible="true" width="56.0078125" x="18.49609375" y="5.6494140625">%s</y:NodeLabel>' % (self.label))
        out.write('<y:Shape type="%s"/>' % (self.shape))
        out.write('</y:ShapeNode>')
        out.write('</data>')
        out.write('</node>\n')
    
    def __str__(self):
        return self.label

class Edge(object):
    def __init__(self, graph, fromNode, toNode, **kwargs):
        graph.edges.append(self)
        self.id = graph.nextId()
        self.fromNode = fromNode
        self.toNode = toNode
        self.sourceArrow = "none"
        self.targetArrow = "standard"
        for key, value in kwargs.items():
        	self.__setattr__(key, value)
    
    def write(self, out):
        out.write('<edge id="e%d" source="n%d" target="n%d">' % (self.id, self.fromNode.id, self.toNode.id))
        out.write('<data key="d6"/>')
        out.write('<data key="d7">')
        out.write('<y:PolyLineEdge>')
        out.write('<y:Path sx="0.0" sy="0.0" tx="0.0" ty="0.0"/>')
        out.write('<y:LineStyle color="#000000" type="line" width="1.0"/>')
        out.write('<y:Arrows source="%s" target="%s"/>' % (self.sourceArrow, self.targetArrow))
        out.write('<y:BendStyle smoothed="false"/>')
        out.write('</y:PolyLineEdge>')
        out.write('</data>')
        out.write('</edge>\n')

class UndirectedEdge(Edge):
    def __init__(self, graph, fromNode, toNode):
        Edge.__init__(self, graph, fromNode, toNode, sourceArrow="none", targetArrow="none")

if __name__ == "__main__":
    g = Graph()
    n = Node(g, label = "Hello")
    n2 = Node(g, label = "World")
    Edge(g, n, n2)
    g.write(file("test.graphml", "w"))
