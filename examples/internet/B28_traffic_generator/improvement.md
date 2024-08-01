# Improvement 

Here are suggested improvement:

- Add a note section in README regarding the following:
  - The `debug` option of the `iperf` affects the bitrate of the testing. This is because
    it prints out a lot of messages on the main terminal (consuming bandwidth
    and CPU cycles). In the example, we should turn it off. 

  - Don't use the Internet map to visualize the traffic, because that will 
    create a lot of additional network traffic, affecting the testing results. 

- For the `scapy` example, if you can suppress the following output, that will
  be great. It messes up the main terminal. Try to redirect it to /dev/null
    ```
    as150h-scapy-generator-10.150.0.73  | Sent 1 packets.
    as150h-scapy-generator-10.150.0.73  |
    as150h-scapy-generator-10.150.0.73  | Sent 1 packets.
    as150h-scapy-generator-10.150.0.73  |
    ```

- In the README file, try to avoid using screenshots; instead, copy and paste
  the contents (which are all text) on the screen, and include only the text
  in the file. We only use screenshots if there are graphic contents. 
  You can remove those pictures.


- The video demos are not needed for README. Github won't display them anyway. 
  You can remove those video as well.

- For the example, I have reduced the default time to 120 seconds for the 
  DITG example, or the log file size is quite big. I also increase the number
  of receivers to 2.

- For the DITG example, use `tc` to reduce the bandwidth of the network of 
  one of the receiver, and see the difference of the results. This will make
  an interesting experiment. We can run the `tc` command manually after the 
  emulator starts. Describe the command in the manual. 

- For each of the example, use a sentence or two to describe what the tool
  will do. If at the beginning, we can give a summary on their main differences,
  that will be great. 

- I don't see the need for the hybrid service. The choices in this service are hardcoded. 
  Instead, we should just create an example, which uses multiple generators and 
  receivers. This will achieve the same goal. 

