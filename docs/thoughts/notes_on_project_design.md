# API Design Thoughts

Kevin Du<br>
September 19, 2020 

My vision on the emulator changed in the last few days while I am doing the programming (I am glad that I did this). Initially we were trying to build a software that reads a configuration file and then create the emulator. That's why we spent a lot of time on the configuration file. Now, my vision has evolved, now our goal is to build the emulator as a Python module, not as a complete software. Users can use our Python module to build their own emulator. It just occurred to me this morning that with this vision, the configuration is not necessary (is good to have), because users can call our APIs to add an AS, a network, a peering, etc. No configuration language we develop can match the expression power of a programming language like Python.

This reminds me of Scapy and the other packet-creation tools that we used before. No single packet-creation tool can match the power of Scapy. Most these tools allow you to have a "configuration file" (i.e., the command-line arguments or GUI interface), for simple protocols (like IP), they are ok, but once the protocol gets complicated (like DNS), those tools become very limited, but Scapy does not have such a limitation, because with Scapy, you simply call its API to build packets, and you can set every single field of a packet. Scapy's API is very well designed, something that we should learn from.

In our API design, we will provide a "loadFromFile" API for the configuration file, but this is not the only way to build a emulator. In this API, we can use the postfix to identify the type of the configuration file. If it is csv, it will call the code I wrote; if it is .conf, it will call the code you wrote. In the future, we can support more formats.

However, I don't want to focus on the configuration file any more. I want to focus on the API design, so users can use our API to build the emulator, instead of using a configuration file. On this Monday's meeting, we will focus on the API design, so give it some thoughts, write down the API for the new objects classes that you think we need. Think about the new APIs that are needed for the existing classes, and so on.