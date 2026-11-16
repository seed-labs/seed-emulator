# DNS Component Demo

In this example, we demonstrate the component concepts using DNS. 
This example has two parts: `dns-dump.py` and `dns-load.py`.

## Creating and saving the component

We first create a simple DNS infrastructure and 
then export this entire infrastructure as a component, i.e.,
saving it in a file.

```python
emu.addLayer(dns)
emu.dump('dns-component.bin')
```

## Loading a pre-built component

We then load the file in another emulator program, and restore the 
entire DNS infrastructure. This shows how a component built from
another emulator can be used by another emulator. 


```python
emu = Emulator()
emu.load('dns-component.bin')
dns: DomainNameService = emu.getLayer('DomainNameService')
```

## Notes

This example only demonstrate the dump and load functionalities. 
How to incorporate the pre-built component in building another 
emulator can be found in other examples. 


