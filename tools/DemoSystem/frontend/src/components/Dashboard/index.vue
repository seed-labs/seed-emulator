<script setup lang="ts">
import VideoCarousel from "@/components/VideoCarousel/index.vue"
import type {VideoItem} from "@/components/VideoCarousel/index.vue"

export interface GridItem {
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
    img: new URL('@/assets/img/seed.png', import.meta.url).href,
    toName: 'home',
    title: '海洋世界',
    description: 'The network topology diagram displays interconnection relationships between nodes and networks, along with auxiliary functions including filtering, search, settings, replay, and logging.',
  },
  {
    img: new URL('@/assets/img/seed.png', import.meta.url).href,
    toName: 'home',
    title: '美丽风景',
    description: 'The network topology diagram displays interconnection relationships between nodes and networks, along with auxiliary functions including filtering, search, settings, replay, and logging.',
  },
  {
    img: new URL('@/assets/img/seed.png', import.meta.url).href,
    toName: 'home',
    title: '城市风光',
    description: 'The network topology diagram displays interconnection relationships between nodes and networks, along with auxiliary functions including filtering, search, settings, replay, and logging.',
  },
  {
    img: new URL('@/assets/img/seed.png', import.meta.url).href,
    toName: 'home',
    title: '科技未来',
    description: 'The network topology diagram displays interconnection relationships between nodes and networks, along with auxiliary functions including filtering, search, settings, replay, and logging.',
  },
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
    <el-card>
      <template #header>
        <div class="card-title">{{ props.title }}</div>
      </template>
      <VideoCarousel :videos="videoList"/>
    </el-card>
    <el-card>
      <ul class="custom-grid">
        <li v-for="item in gridList" :key="item.title">
          <router-link :to="{ name: item.toName }">
            <el-tooltip
                class="box-item"
                effect="dark"
                :content="item.description"
                placement="bottom-start"
            >
              <el-card>
                <template #header>
                  <div class="card-title">{{ item.title }}</div>
                </template>
                <el-image :src="item.img" style="height: 200px;"/>
              </el-card>
            </el-tooltip>
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
  margin: 0 auto;
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
</style>