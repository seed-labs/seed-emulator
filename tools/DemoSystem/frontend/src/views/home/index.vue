<script setup lang="ts">
import Dashboard from "@/components/Dashboard/index.vue"
import type {GridItem} from "@/components/Dashboard/index.vue"
import type {VideoItem} from "@/components/VideoCarousel/index.vue"

const title = "网络仿真演示平台"
const videoList: VideoItem[] = [
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: 'BGP 前缀劫持',
    description: '结合 SEEDEMU 仿真器的 BGP 探索和攻击'
  },
  {
    src: new URL('@/assets/video/morris-demo-new.mp4', import.meta.url).href,
    title: 'morris worm 蠕虫',
    description: '结合 SEEDEMU 仿真器的 Morris worm 蠕虫'
  },
]

const gridList: GridItem[] = [
  {
    name: 'bgp',
    img: new URL('@/assets/img/bgp_exploration.png', import.meta.url).href,
    toName: 'common',
    title: 'BGP 前缀劫持',
    description: '边界网关协议（BGP）是用于在互联网上的自治系统（AS）之间交换路由和可达性信息的标准外部网关协议。它是互联网的“粘合剂”，是互联网基础设施的重要组成部分，也是主要的攻击目标之一。如果攻击者能够控制 BGP，则可以断开互联网并重定向流量。本实验的目标是帮助学生了解 BGP 如何将互联网连接在一起以及互联网是如何连接的。我们构建了一个互联网仿真器，并将使用此仿真器作为实验活动的基础。',
  },
  {
    name: 'morris',
    toName: 'common',
    img: new URL('@/assets/img/worm.png', import.meta.url).href,
    title: 'Morris worm 蠕虫',
    description: '莫里斯蠕虫（1988年11月）是通过互联网传播的最古老的计算机蠕虫之一。虽然它很古老，但今天大多数蠕虫使用的技术仍然是相同的。它们包括两个主要部分：攻击和自我复制。攻击部分利用一个漏洞（或几个漏洞），因此蠕虫可以进入另一台计算机。自我复制部分是将自己的副本发送到受感染的机器，然后从那里发动攻击。',
  }
]

</script>

<template>
  <Dashboard
      :title="title"
      :video-list="videoList"
      :grid-list="gridList"
  />

</template>

<style scoped>

</style>