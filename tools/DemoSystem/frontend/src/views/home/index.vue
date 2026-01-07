<script setup lang="ts">
import Dashboard from "@/components/Dashboard/index.vue"
import type {GridItem} from "@/components/Dashboard/index.vue"
import type {VideoItem} from "@/components/VideoCarousel/index.vue"

const title = "网络仿真演示平台"
const videoList: VideoItem[] = [
  {
    src: new URL('@/assets/video/demo1.mp4', import.meta.url).href,
    title: '大规模互联网仿真演示',
    description: 'moodle框架'
  },
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: '大规模区块链仿真演示',
    description: '探索神秘的海底世界，与海洋生物共舞'
  },
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: '“昨日重现”演示',
    description: '欣赏大自然的壮丽景色，感受宁静与和谐'
  },
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: '自动 CTF 靶场',
    description: '现代都市的繁华景象，快节奏的生活方式'
  },
]

const gridList: GridItem[] = [
  {
    img: new URL('@/assets/img/seed.png', import.meta.url).href,
    toName: 'large-scale-internet-simulation',
    title: '大规模互联网仿真演示',
    description: 'The network topology diagram displays interconnection relationships between nodes and networks, along with auxiliary functions including filtering, search, settings, replay, and logging.',
  },
  {
    img: new URL('@/assets/img/seed.png', import.meta.url).href,
    toName: 'large-scale-blockchain-simulation',
    title: '大规模区块链仿真演示',
    description: 'The network topology diagram displays interconnection relationships between nodes and networks, along with auxiliary functions including filtering, search, settings, replay, and logging.',
  },
  {
    img: new URL('@/assets/img/seed.png', import.meta.url).href,
    toName: 'yesterday-reenacted',
    title: '“昨日重现”演示',
    description: 'The network topology diagram displays interconnection relationships between nodes and networks, along with auxiliary functions including filtering, search, settings, replay, and logging.',
  },
  {
    img: new URL('@/assets/img/seed.png', import.meta.url).href,
    toName: 'auto-CTF',
    title: '自动 CTF 靶场',
    description: 'The network topology diagram displays interconnection relationships between nodes and networks, along with auxiliary functions including filtering, search, settings, replay, and logging.',
  },
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