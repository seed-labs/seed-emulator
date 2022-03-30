interface PluginInterface {
  emit: (data:object) => void;
  attach:(event:string, params:string) => void;
  structureData:(data: object) =>void;
}

export default PluginInterface;