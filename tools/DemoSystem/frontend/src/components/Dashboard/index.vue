<script setup lang="ts">
import VideoCarousel from "@/components/VideoCarousel/index.vue"
import type {VideoItem} from "@/components/VideoCarousel/index.vue"

export interface GridItem {
  name: string
  path: string
  img: string
  title: string
  description: string
}

interface Props {
  title?: string;
  videoList?: VideoItem[];
  gridList?: GridItem[];
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Dashboard',
  videoList: () => [],
  gridList: () => []
});

const emptyDes = "尚未发布，尽请期待..."

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
      <div class="empty-holder" v-if="gridList.length === 0">
        <el-empty :image-size="600" style="position: static !important;">
          <template #description>
            {{ emptyDes }}
          </template>
        </el-empty>
      </div>
      <ul v-else class="custom-grid">
        <li v-for="item in gridList" :key="item.title">
          <router-link class="dashboard-link" :to="item.path">
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

<style lang="scss">
.el-empty {
  width: 100%;
  height: 100%;
  border: none;

  .el-empty__description {
    font-size: 50px;
    color: #ff4d4f;
    font-weight: 600;
    line-height: 1.5;
  }
}
</style>