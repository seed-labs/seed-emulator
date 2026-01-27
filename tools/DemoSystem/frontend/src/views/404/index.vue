<template>
  <div class="no-found">
    <img src="@/assets/img/404.png">
    <div class="home-btn">
      <el-button @click="goHome" class="btn1" type="primary" size="large">返回首页</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import {useRouter} from 'vue-router'

const router = useRouter()
const goHome = () => {
  router.push("/")
}
</script>

<style scoped lang="scss">
.no-found {
  display: flex;
  justify-content: center;
  flex-direction: column;

  img {
    width: 100vw;
    height: 100vh;
  }

  .home-btn {
    position: absolute;
    top: 2%;
    right: 2%;
  }
}
</style>