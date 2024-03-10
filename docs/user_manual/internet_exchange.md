# User Manual: Internet Exchange 


<a id="default-settings"></a>
## Default Settings

In essence, an Internet exchange is basically a high throughput LAN. 

- Name: The name for an Internet exchange 
is set to `ix{asn}`, where `{asn}` is the autonomous system number of 
the Internet exchange. For example, for an Internet exchange with ASN=100, 
the name is set to `ix100`. This naming mechanism is fixed for now. 

- Network prefix: The default network prefix for an IX is set to 
  `10.{asn}.0.0/24`. However, users can override this default 
  setting using the `prefix` parameter when creating an IX. 
  ```python
  ix100 = base.createInternetExchange(100, prefix='192.168.10.0/24')
  ```


<a id="customization"></a>
## Customization


```python
ix100 = base.createInternetExchange(100)
ix101 = base.createInternetExchange(101)

# Customize names (for visualization purpose)
ix100.getPeeringLan().setDisplayName('New York-100')
ix101.getPeeringLan().setDisplayName('Los Angeles-101')
```
