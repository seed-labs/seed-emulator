export const baseInfo = {
  "name": "Mirai 僵尸网络攻击",
  "path": "./yesterday_once_more/03_mirai"
}

export const config = [
  {
    "headerTitle": "启动靶场",
    "text": [
      {
        "shortText": null,
        "cmdKwargs": [
          {
            "type": "command_only",
            "action": "host_exec",
            "cmd": "cd $hostProjectPath/yesterday_once_more/03_mirai/demo/demo_output && docker compose up -d"
          }
        ]
      }
    ]
  },
  {
    "headerTitle": "环境设置",
    "text": [
      {
        "shortText": "环境设置",
        "innerHtml": "<div>首先，我们需要启动仿真器。</div>\n<div>在本实验中，我们需要安装`submit_event`插件。</div>\n<div class=\"code-block\">\n    <div class=\"code-header\">\n        <span class=\"code-title\">命令</span>\n    </div>\n    <pre class=\"code-content\">curl -X POST -H &quot;Content-Type: application/json&quot; -d &#039;{&quot;name&quot;: &quot;submit_event&quot;}&#039; http://&lt;hostname&gt;:8080/api/v1/install</pre>\n</div>",
        "cmdKwargs": [
          {
            "action": "host_exec",
            "cmd": "/usr/bin/curl -X POST -H \\\"Content-Type: application/json\\\" -d '{\\\"name\\\": \\\"submit_event\\\"}' \\\"http://$hostname:8080/api/v1/install\\\"\n"
          }
        ]
      }
    ]
  },
  {
    "headerTitle": "构建僵尸网络",
    "text": [
      {
        "shortText": "启动 C2 服务器",
        "innerHtml": "<div>C2 服务器是僵尸网络的控制中心，用于接收`bot`的连接并发布指令。本示例使用开源工具 BYOB 作为 C2 框架。</div>\n<div class=\"code-block\">\n    <div class=\"code-header\">\n        <span class=\"code-title\">命令</span>\n    </div>\n    <pre class=\"code-content\">./yesterday_once_more/03_mirai/scripts/start_c2_server.sh</pre>\n</div>",
        "cmdKwargs": [
          {
            "action": "host_exec",
            "cmd": "cd $hostProjectPath/yesterday_once_more/03_mirai/scripts/ && /bin/bash start_c2_server.sh"
          }
        ]
      },
      {
        "shortText": "蠕虫控制",
        "innerHtml": "<div>C2 服务准备就绪后，即可释放蠕虫。我们将从 C2 服务器本身开始，运行 mirai.py 脚本。它将作为第一个被感染的节点，扫描网络中其他具有弱 Telnet 凭据的设备，并植入自身的副本</div>\n<div>现在，执行下面的代码单元以启动蠕虫。</div>\n<div class=\"code-block\">\n    <div class=\"code-header\">\n        <span class=\"code-title\">命令</span>\n    </div>\n    <pre class=\"code-content\">print(&quot;正在 C2 服务器上释放 &#039;mirai.py&#039; 蠕虫...&quot;)\nc2_container_id = !docker ps -f &quot;name=C2_server&quot; -q\nif c2_container_id:\n    !docker exec -d {c2_container_id[0]} sh -c &#039;cd /var/www/html/ &amp;&amp; python3 mirai.py &gt; /tmp/mirai_worm.log 2&gt;&amp;1&#039;\n    print(&quot;蠕虫已在后台运行，将开始扫描并感染网络中的其他主机。&quot;)\nelse:\n    print(&quot;错误：未找到 C2_server 容器。&quot;)</pre>\n</div>\n<div>执行上一步后，蠕虫已开始传播。请切换到 Internet map 进行观察（短暂闪烁后高亮）。</div>\n<div>您将看到新的节点不断发起与 C2 服务器的连接，这表明这些节点正在下载 mirai.py 蠕虫脚本。整个传播过程的流量动态将直观地呈现在您面前。</div>\n<div>同时，在运行 BYOB 的终端中，您会看到新的会话连接消息出现。当网络被完全感染时，会话总数将超过 90 个，可作为传播进度的参考。</div>",
        "cmdGroupKwargs": [
          {
            "title": "release",
            "tooltip": "释放蠕虫",
            "cmdKwargs": [
              {
                "action": "docker_exec",
                "containerNames": [
                  "as170h-C2_server-10.170.0.100"
                ],
                "cmd": "cd /var/www/html/ && python3 mirai.py > /tmp/mirai_worm.log 2>&1",
                "detach": true
              }
            ]
          },
          {
            "title": "stop",
            "tooltip": "停止蠕虫",
            "cmdKwargs": [
              {
                "action": "host_exec",
                "cmd": "cd $hostProjectPath/yesterday_once_more/03_mirai/scripts && /bin/bash ./control_worm.sh stop"
              }
            ]
          }
        ]
      }
    ]
  },
  {
    "headerTitle": "Botnet",
    "text": [
      {
        "shortText": "Botnet 控制",
        "innerHtml": "<div>使用 `broadcast` 控制 Botnet</div>\n<div>切换到运行 BYOB 控制台的终端窗口，键入以下命令并回车。此命令将被广播给所有在线的 `bot`。</div>\n<div>请切换到 Internet map 进行观察（闪烁）。</div>\n<div class=\"code-block\">\n    <div class=\"code-header\">\n        <span class=\"code-title\">命令</span>\n    </div>\n    <pre class=\"code-content\"># 在 BYOB 控制台中输入命令：\n\n# display\nbroadcast timeout 300s bash -c &#039;\n/usr/bin/echo &quot;{ \\&quot;flash\\&quot;: { \\&quot;dynamic\\&quot;: { \\&quot;borderWidth\\&quot;: 8, \\&quot;size\\&quot;: 50 }, \\&quot;duration\\&quot;: 1000 } }&quot; &gt;/map-plugins/style.json \n&amp;&amp; /bin/bash /map-plugins/submit_event.sh -a flash -s /map-plugins/style.json &gt; /dev/null 2&gt;&amp;1&#039;\n\n# restore\nbroadcast timeout 30s bash -c &#039;/bin/bash /map-plugins/submit_event.sh \n-a restore &gt; /dev/null 2&gt;&amp;1&#039;</pre>\n</div>",
        "cmdGroupKwargs": [
          {
            "title": "display",
            "tooltip": "展示",
            "cmdKwargs": [
              {
                "action": "terminal_exec",
                "containerName": "as170h-C2_server-10.170.0.100",
                "cmd": "broadcast timeout 60s bash -c '/usr/bin/echo \"{ \\\"flash\\\": { \\\"dynamic\\\": { \\\"borderWidth\\\": 8, \\\"size\\\": 50 }, \\\"duration\\\": 1000 } }\" >/map-plugins/style.json && /bin/bash /map-plugins/submit_event.sh -a flash -s /map-plugins/style.json && sleep 5 && /bin/bash /map-plugins/submit_event.sh -a highlight > /dev/null 2>&1'\n"
              }
            ]
          },
          {
            "title": "restore",
            "tooltip": "恢复",
            "cmdKwargs": [
              {
                "action": "terminal_exec",
                "containerName": "as170h-C2_server-10.170.0.100",
                "cmd": "broadcast timeout 30s bash -c '/bin/bash /map-plugins/submit_event.sh -a restore > /dev/null 2>&1'\n"
              }
            ]
          }
        ]
      },
      {
        "shortText": "Botnet 攻击",
        "innerHtml": "<div>切换到运行 BYOB 控制台的终端窗口，键入以下命令并回车。此命令将被广播给所有在线的 `bot`。</div>\n<div>请切换到 Internet map 进行观察（数据包数量统计）。</div>\n<div class=\"code-block\">\n    <div class=\"code-header\">\n        <span class=\"code-title\">命令</span>\n    </div>\n    <pre class=\"code-content\"># 在 BYOB 控制台中输入此命令：\nbroadcast timeout 30s bash -c &#039;ping 10.170.0.99 &gt; /dev/null 2&gt;&amp;1&#039;</pre>\n</div>",
        "cmdGroupKwargs": [
          {
            "title": "attack",
            "tooltip": "发起攻击",
            "cmdKwargs": [
              {
                "action": "terminal_exec",
                "containerName": "as170h-C2_server-10.170.0.100",
                "cmd": "broadcast timeout 30s bash -c 'ping 10.170.0.99 > /dev/null 2>&1'\n"
              },
              {
                "action": "host_exec",
                "cmd": "/usr/bin/curl -X POST -H \\\"Content-Type: application/json\\\" -d '{\\\"nodeName\\\": \\\"/as170h-victim-10.170.0.99\\\", \\\"filter\\\": \\\"dst 10.170.0.99\\\"}' \\\"http://$hostname:8080/api/v1/packet\\\"\n"
              }
            ]
          },
          {
            "title": "restore",
            "tooltip": "恢复",
            "cmdKwargs": [
              {
                "action": "terminal_exec",
                "containerName": "as170h-C2_server-10.170.0.100",
                "cmd": "broadcast bash -c 'pkill -f \"ping 10.170.0.99\"'\n"
              },
              {
                "action": "host_exec",
                "cmd": "/usr/bin/curl -X POST -H \\\"Content-Type: application/json\\\" -d '{\\\"nodeName\\\": \\\"/as170h-victim-10.170.0.99\\\", \\\"action\\\": \\\"restore\\\"}' \\\"http://$hostname:8080/api/v1/packet\\\"\n"
              }
            ]
          }
        ]
      }
    ]
  },
  {
    "headerTitle": "关闭靶场",
    "text": [
      {
        "shortText": null,
        "cmdKwargs": [
          {
            "type": "command_only",
            "action": "host_exec",
            "cmd": "cd $hostProjectPath/yesterday_once_more/03_mirai/demo/demo_output && docker compose down"
          }
        ]
      }
    ]
  }
]

export default config
