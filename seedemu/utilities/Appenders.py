from seedemu import *

# move this to utility
def addNodes(self, emu:Emulator, baseFile:str):
    output = "output"
    baseEmulator = Emulator()
    baseEmulator.load(baseFile)
    baseEmulator.render()
    emu.render()

    newNodes = emu.getRegistry().getAll().keys() - baseEmulator.getRegistry().getAll().keys()

    cur = getcwd()
    if path.exists(output):
        rmtree(output)
        
    mkdir(output)
    chdir(output)

    for scope, type, name in newNodes:
        self._addNode(emu, scope=scope, type=type, name=name, rendered=True, output=output)

    chdir(cur)

def addNode(self, emu:Emulator, scope:str, name:str, type:str='hnode', rendered:boolean=False, output:str="output"):
        client = self.__client 
        
        if not rendered:
            emu.render()

        obj = emu.getRegistry().get(type=type, scope=scope, name=name)
        docker = Docker()

        buildPath = "_".join([type, scope, name])
        
        
        dcInfo = yaml.safe_load(docker._compileNode(obj))[buildPath]

        networks = list(dcInfo['networks'].keys())