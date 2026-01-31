<script setup lang="ts">
import VideoCarousel from "@/components/VideoCarousel/index.vue"
import type {VideoItem} from "@/components/VideoCarousel/index.vue"

export interface GridItem {
  name: string
  img: string
  title: string
  description: string
  toName: string
}

/* ------------------- 视频资源 ------------------- */
const defaultVideoList: VideoItem[] = [
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: '海洋世界',
    description: '探索神秘的海底世界，与海洋生物共舞'
  },
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: '美丽风景',
    description: '欣赏大自然的壮丽景色，感受宁静与和谐'
  },
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: '城市风光',
    description: '现代都市的繁华景象，快节奏的生活方式'
  },
  {
    src: 'https://vjs.zencdn.net/v/oceans.mp4',
    title: '科技未来',
    description: '前沿科技展示，感受未来生活的无限可能'
  },
]

const defaultGridList: GridItem[] = [
  {
    name: 'bgp',
    img: new URL('@/assets/img/bgp_exploration.png', import.meta.url).href,
    toName: 'common',
    title: 'BGP 前缀劫持',
    description: '边界网关协议（BGP）是用于在互联网上的自治系统（AS）之间交换路由和可达性信息的标准外部网关协议。它是互联网的“粘合剂”，是互联网基础设施的重要组成部分，也是主要的攻击目标之一。如果攻击者能够控制 BGP，则可以断开互联网并重定向流量。',
  },
  {
    name: 'morris',
    toName: 'common',
    img: new URL('@/assets/img/worm.png', import.meta.url).href,
    title: 'morris worm 蠕虫',
    description: '莫里斯蠕虫（1988年11月）是通过互联网传播的最古老的计算机蠕虫之一。虽然它很古老，但今天大多数蠕虫使用的技术仍然是相同的。它们包括两个主要部分：攻击和自我复制。攻击部分利用一个漏洞（或几个漏洞），因此蠕虫可以进入另一台计算机。自我复制部分是将自己的副本发送到受感染的机器，然后从那里发动攻击。',
  }
]

interface Props {
  title?: string;
  videoList?: VideoItem[];
  gridList?: GridItem[];
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Dashboard',
});

const videoList = props.videoList?.length ? props.videoList : defaultVideoList
const gridList = props.gridList?.length ? props.gridList : defaultGridList
</script>

<template>
  <el-space direction="vertical" style="align-items: normal; width: 100%">
    <!--    <el-card>-->
    <!--      <template #header>-->
    <!--        <div class="card-title">{{ props.title }}</div>-->
    <!--      </template>-->
    <!--      <VideoCarousel :videos="videoList"/>-->
    <!--    </el-card>-->
    <el-card>
      <template #header>
        <div class="card-title">{{ props.title }}</div>
      </template>
      <ul class="custom-grid">
        <li v-for="item in gridList" :key="item.title">
          <router-link class="dashboard-link" :to="{ name: item.toName, query: { name: item.name }}">
            <el-card>
              <template #header>
                <div class="card-title">{{ item.title }}</div>
              </template>
              <el-image :src="item.img"/>
              <el-text class="dashboard-text">{{ item.description }}</el-text>
            </el-card>
          </router-link>
        </li>
      </ul>
    </el-card>
  </el-space>
</template>

<style scoped lang="scss">
.custom-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 100px;
  list-style: none;
  padding: 20px;
  margin: 300px auto;
  width: 80%;
}

.el-carousel__item h3 {
  color: #475669;
  opacity: 0.75;
  line-height: 200px;
  margin: 0;
  text-align: center;
}

.el-carousel__item:nth-child(2n) {
  background-color: #99a9bf;
}

.el-carousel__item:nth-child(2n + 1) {
  background-color: #d3dce6;
}

.card-title {
  font-size: 30px; /* 字号 */
  font-weight: 600; /* 粗细 */
  color: #2c3e50; /* 文字颜色 */
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; /* 字体 */
}

.dashboard-link {
  text-decoration: none; /* 去除下划线 */
}

.dashboard-text {
  font-size: 16px;
  color: #333;
  font-family: 'Microsoft YaHei', sans-serif;
  font-weight: 800;
}
</style>