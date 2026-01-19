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
            "cmd": "cd $hostProjectPath/yesterday_once_more/02_morris_worm/emulator/demo_output && ./z_start.sh"
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
        "innerHtml": "<div>首先，我们需要启动仿真器。</div>\n<div>在本实验中，我们需要关闭地址随机化。这个内核参数是全局的，所以一旦我们在主机上关闭它，所有容器都会受到影响。</div>\n<div class=\"code-block\">\n    <div class=\"code-header\">\n        <span class=\"code-title\">命令</span>\n    </div>\n    <pre class=\"code-content\">sudo -S /sbin/sysctl -w kernel.randomize_va_space=0\ncurl -X POST -H &quot;Content-Type: application/json&quot; -d &#039;{&quot;name&quot;: &quot;submit_event&quot;}&#039; http://localhost:8080/api/v1/install</pre>\n</div>",
        "cmdKwargs": [
          {
            "action": "host_exec",
            "cmd": "cd $hostProjectPath/yesterday_once_more/02_morris_worm/worm/ && /bin/bash setup.sh"
          },
          {
            "action": "host_exec",
            "cmd": "/usr/bin/curl -X POST -H \\\"Content-Type: application/json\\\" -d '{\\\"name\\\": \\\"submit_event\\\"}' \\\"http://localhost:8080/api/v1/install\\\"\n"
          }
        ]
      }
    ]
  },
  {
    "headerTitle": "执行攻击",
    "text": [
      {
        "shortText": "执行攻击",
        "innerHtml": "<div>执行 ./yesterday_once_more/02_morris_worm/worm/first_attack.py 发起攻击</div>",
        "cmdKwargs": [
          {
            "action": "host_exec",
            "cmd": "cd $hostProjectPath/yesterday_once_more/02_morris_worm/worm && $condaPath run -n $envName python first_attack.py"
          }
        ]
      }
    ]
  },
  {
    "headerTitle": "蠕虫控制",
    "text": [
      {
        "shortText": "蠕虫控制",
        "innerHtml": "<div>通过项目根目录下的 ./yesterday_once_more/02_morris_worm/worm/control_worm.sh 控制蠕虫</div>\n<div class=\"code-block\">\n    <div class=\"code-header\">\n        <span class=\"code-title\">命令</span>\n    </div>\n    <pre class=\"code-content\">control_worm.sh\n  run\n  stop\n  pause\n  show\n  off</pre>\n</div>",
        "cmdGroupKwargs": [
          {
            "title": "run",
            "tooltip": "运行蠕虫",
            "cmdKwargs": [
              {
                "action": "host_exec",
                "cmd": "cd $hostProjectPath/yesterday_once_more/02_morris_worm/worm && /bin/bash ./control_worm.sh run"
              }
            ]
          },
          {
            "title": "stop",
            "tooltip": "停止蠕虫",
            "cmdKwargs": [
              {
                "action": "host_exec",
                "cmd": "cd $hostProjectPath/yesterday_once_more/02_morris_worm/worm && /bin/bash ./control_worm.sh stop"
              }
            ]
          },
          {
            "title": "pause",
            "tooltip": "暂停蠕虫",
            "cmdKwargs": [
              {
                "action": "host_exec",
                "cmd": "cd $hostProjectPath/yesterday_once_more/02_morris_worm/worm && /bin/bash ./control_worm.sh pause"
              }
            ]
          },
          {
            "title": "show",
            "tooltip": "在 Map 上展示",
            "cmdKwargs": [
              {
                "action": "host_exec",
                "cmd": "cd $hostProjectPath/yesterday_once_more/02_morris_worm/worm && /bin/bash ./control_worm.sh show"
              }
            ]
          },
          {
            "title": "off",
            "tooltip": "在 Map 上隐藏",
            "cmdKwargs": [
              {
                "action": "host_exec",
                "cmd": "cd $hostProjectPath/yesterday_once_more/02_morris_worm/worm && /bin/bash ./control_worm.sh off"
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
            "action": "docker_compose",
            "cmd": "composeDown",
            "detach": false,
            "composePath": "./yesterday_once_more/02_morris_worm/emulator/demo_output"
          }
        ]
      }
    ]
  }
]

export default config
