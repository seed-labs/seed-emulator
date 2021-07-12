# Add DNS Infrastructure to Base

## Virtual Nodes in the DNS Infrastructure

- a-com-server
- b-com-server
- a-net-server
- a-edu-server
- a-cn-server
- b-cn-server
- ns-twitter-com
- ns-google-com
- ns-example-net
- ns-syr-edu
- ns-weibo-cn

## Suggestions

- Several DNS-related APIs should return `self` to allow API chaining
- Use `Action.NEW` to map a virtual node to a new physical node (create one)

