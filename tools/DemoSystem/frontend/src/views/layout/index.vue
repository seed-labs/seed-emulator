<template>
  <el-container style="height: 100vh;">
    <el-header>
      <el-menu
          :default-active="defaultActive"
          class="menu"
          mode="horizontal"
          unique-opened
          router
      >
        <el-menu-item index="0" class="logo-item">
          <img
              style="height: 80%;"
              src="@/assets/img/seed.png"
              alt="logo"
          />
        </el-menu-item>
        <div class="right-items">
          <el-menu-item index="/home">首页</el-menu-item>
          <el-sub-menu index="common">
            <template #title>昨日重现</template>
            <el-menu-item index="/common?name=bgp">BGP 前缀劫持</el-menu-item>
            <el-menu-item index="/common?name=morris">Morris worm 蠕虫</el-menu-item>
          </el-sub-menu>
        </div>
      </el-menu>
    </el-header>
    <el-main>
      <router-view/>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import {useRoute} from 'vue-router';

const route = useRoute();
const defaultActive = ref<string>(route.path)
</script>

<style scoped lang="scss">
.menu {
  display: flex;
  align-items: center;
  justify-content: space-between;

  .right-items {
    display: flex;
    align-items: center;
  }

  .el-menu .el-menu-item-group .el-menu-item {
    font-size: 12px;
  }

  /* 自定义激活样式 */
  .el-sub-menu.is-active :deep(.el-sub-menu__title) {
    color: var(--el-color-primary) !important;
    border-bottom-color: var(--el-color-primary) !important;
  }
}

.dashboard-link {
  text-decoration: none; /* 去除下划线 */
}
</style>

