import sys
import re

#Parse PMML into GraphML files

class Node:
    def __init__(self,desc):
        self.nodeDict = {"name": "", "id": "", "x": "", "y": "", "type": "", "parents": []}
        self.parse(desc)
    def parse(self,desc):
        name = re.compile("name=\"(.*)\" optype")
        nodeId = re.compile("id=\"(\S*)\"")
        nodeType = re.compile("<X-NodeType>(\S*)</X-NodeType>")
        x = re.compile("x=\"(\S*)\"")
        y = re.compile("y=\"(\S*)\"")
        parents = re.compile("<X-Given>(\d*)</X-Given>")
        reDict = {"name" : name, "id": nodeId, "x": x, "y": y, "type": nodeType, "parents": parents }
        for line in desc:
            for expr in reDict:
                f = reDict[expr].findall(line)
                if f != []:
                    if expr == "parents":
                        self.nodeDict["parents"].append(f[0])
                    else:
                        self.nodeDict[expr] = f[0]
    def getGraphML(self):
        ret = []
        width = max(float(len(self.nodeDict["name"]))*7,35)
        ret.append('<node id="n%s">' %(self.nodeDict["id"]))
        ret.append('<data key="d2"/>')
        ret.append('<data key="d3">')
        #Shape of node, depending on whether decision node or random variable:
        if self.nodeDict["type"] == "chance":
            shapeType = "ellipse"
            color = "#B1CBDA"
        else:
            shapeType = "rectangle"
            color = "#45CA46" # "#00FF00"
        ret.append('<y:ShapeNode>')
        ret.append('<y:Geometry height="30.0" width="%s" x="%s" y="%s"/>' %(str(width),self.nodeDict["x"],self.nodeDict["y"]))
        ret.append('<y:Fill color="%s" transparent="false"/>' %(color))
        ret.append('<y:BorderStyle color="#000000" type="line" width="1.0"/>')
        ret.append('<y:NodeLabel alignment="center" autoSizePolicy="content" fontFamily="Dialog" fontSize="12" fontStyle="plain" hasBackgroundColor="false" hasLineColor="false" height="18.701171875" modelName="internal" modelPosition="c" textColor="#000000" visible="true" width="56.0078125" x="18.49609375" y="5.6494140625">%s</y:NodeLabel>' %(self.nodeDict["name"]))
        ret.append('<y:Shape type="%s"/>' %(shapeType))
        ret.append('</y:ShapeNode>')
        ret.append('</data>')
        ret.append('</node>')
        return ret
    def getParents(self,startID):
        ret = []
        endID = startID
        for p in self.nodeDict["parents"]:
            ret.append('<edge id="e%s" source="n%s" target="n%s">' %(str(endID),p,self.nodeDict["id"]))
            ret.append('<data key="d6"/>')
            ret.append('<data key="d7">')
            ret.append('<y:PolyLineEdge>')
            ret.append('<y:Path sx="0.0" sy="0.0" tx="0.0" ty="0.0"/>')
            ret.append('<y:LineStyle color="#000000" type="line" width="1.0"/>')
            ret.append('<y:Arrows source="none" target="standard"/>')
            ret.append('<y:BendStyle smoothed="false"/>')
            ret.append('</y:PolyLineEdge>')
            ret.append('</data>')
            ret.append('</edge>')
            endID += 1
        return (ret,endID)

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1][-5:] != ".pmml":
        print("Usage: pmml2graphml *.pmml")
    else:
        name = sys.argv[1][:-5]
        inputFile = open(sys.argv[1],"r")
        lines = inputFile.readlines()
        inputFile.close()

        outputFile = open(name+".graphml","w")

        #Basic Definitions
        #TODO: Make graph design selectable by user
        outputFile.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:y="http://www.yworks.com/xml/graphml" xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns http://www.yworks.com/xml/schema/graphml/1.1/ygraphml.xsd">\n')
        outputFile.write('<key for="graphml" id="d0" yfiles.type="resources"/>\n')
        outputFile.write('<key attr.name="url" attr.type="string" for="node" id="d1"/>\n')
        outputFile.write('<key attr.name="description" attr.type="string" for="node" id="d2"/>\n')
        outputFile.write('<key for="node" id="d3" yfiles.type="nodegraphics"/>\n')
        outputFile.write('<key attr.name="Beschreibung" attr.type="string" for="graph" id="d4">\n')
        outputFile.write('<default/>\n')
        outputFile.write('</key>\n')
        outputFile.write('<key attr.name="url" attr.type="string" for="edge" id="d5"/>\n')
        outputFile.write('<key attr.name="description" attr.type="string" for="edge" id="d6"/>\n')
        outputFile.write('<key for="edge" id="d7" yfiles.type="edgegraphics"/>\n')
        outputFile.write('<graph edgedefault="directed" id="G">\n')

        #Actual Nodes and Edges
        nodes = []
        nodeStart = re.compile('<DataField')
        nodeEnd = re.compile('</DataField')
        for i in range(len(lines)):
            if nodeStart.search(lines[i]) != None:
                startLine = i
            if nodeEnd.search(lines[i]) != None:
                endLine = i
                nodes.append(Node(lines[startLine:endLine]))

        #Add nodes to output file
        for node in nodes:
            gmlOutput = node.getGraphML()
            for i in range(len(gmlOutput)):
                outputFile.write(gmlOutput[i]+"\n")

        #Add edges to output file
        startID = 0
        for node in nodes:
            (edgeOutput,startID) = node.getParents(startID)
            for i in range(len(edgeOutput)):
                outputFile.write(edgeOutput[i]+"\n")

        #Basic End of File
        outputFile.write('</graph>\n')
        outputFile.write('<data key="d0">\n')
        outputFile.write('<y:Resources/>\n')
        outputFile.write('</data>\n')
        outputFile.write('</graphml>\n')
        outputFile.close()