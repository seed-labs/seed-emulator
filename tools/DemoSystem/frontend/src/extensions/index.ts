export const componentRecord = {
    bgp: 'yesterday_once_more/bgp',
    mirai: 'yesterday_once_more/mirai',
    morris: 'yesterday_once_more/morris'
}

export const menus = [
  {
    "name": "home",
    "path": "/dashboard/home",
    "meta": {
      "title": "首页",
      "img": "",
      "description": "",
      "video": {
        "src": "",
        "title": "",
        "description": ""
      }
    }
  },
  {
    "name": "yesterdayOnceMore",
    "path": "/dashboard/yesterdayOnceMore",
    "meta": {
      "title": "昨日重现",
      "img": new URL('@/assets/img/yesterday_once_more.png', import.meta.url).href,
      "description": "通过WEB页面，将历史场景、经典案例或特定状态进行高保真还原的模拟技术。它不仅是一个技术实现的过程，更是一种科研与教学相结合的教学范式",
      "video": {
        "src": "",
        "title": "",
        "description": ""
      }
    },
    "children": [
      {
        "name": "bgp",
        "path": "/dashboard/yesterdayOnceMore/simulation/bgp",
        "meta": {
          "title": "BGP 前缀劫持",
          "img": new URL('@/assets/img/bgp_exploration.png', import.meta.url).href,
          "description": "边界网关协议（BGP）是用于在互联网上的自治系统（AS）之间交换路由和可达性信息的标准外部网关协议。它是互联网的'粘合剂'，是互联网基础设施的重要组成部分，也是主要的攻击目标之一。如果攻击者能够控制 BGP，则可以断开互联网并重定向流量。本实验的目标是帮助学生了解 BGP 如何将互联网连接在一起以及互联网是如何连接的。我们构建了一个互联网仿真器，并将使用此仿真器作为实验活动的基础。",
          "video": {
            "src": "",
            "title": "",
            "description": ""
          }
        }
      },
      {
        "name": "morris",
        "path": "/dashboard/yesterdayOnceMore/simulation/morris",
        "meta": {
          "title": "Morris worm 蠕虫",
          "img": new URL('@/assets/img/worm.png', import.meta.url).href,
          "description": "莫里斯蠕虫（1988年11月）是通过互联网传播的最古老的计算机蠕虫之一。虽然它很古老，但今天大多数蠕虫使用的技术仍然是相同的。它们包括两个主要部分：攻击和自我复制。攻击部分利用一个漏洞（或几个漏洞），因此蠕虫可以进入另一台计算机。自我复制部分是将自己的副本发送到受感染的机器，然后从那里发动攻击。",
          "video": {
            "src": "",
            "title": "",
            "description": ""
          }
        }
      },
      {
        "name": "mirai",
        "path": "/dashboard/yesterdayOnceMore/simulation/mirai",
        "meta": {
          "title": "Mirai 僵尸网络攻击",
          "img": new URL('@/assets/img/mirai.png', import.meta.url).href,
          "description": "近年来物联网（IoT）安全领域最经典、最具代表性的威胁之一。它主要通过暴力破解（Brute Force）手段入侵具有弱密码的网络设备（如路由器、DVR、摄像头等），将其转变为“僵尸”（Bot），并在命令与控制（C&C）服务器的指挥下发起大规模的分布式拒绝服务（DDoS）攻击。",
          "video": {
            "src": "",
            "title": "",
            "description": ""
          }
        }
      }
    ]
  },
  {
    "name": "blockchain",
    "path": "/dashboard/blockchain",
    "meta": {
      "title": "大规模区块链仿真",
      "img": new URL('@/assets/img/large_blockchain.png', import.meta.url).href,
      "description": "跨学科、综合性的科研与教学课题。既要具备区块链理论（共识、加密）的深度，又要有系统工程（网络拓扑、分布式系统）的广度，熟练运用现代工具（Docker、Python 脚本、仿真框架）进行可重复性实验的构建与分析",
      "video": {
        "src": "",
        "title": "",
        "description": ""
      }
    },
    "children": []
  }
]
