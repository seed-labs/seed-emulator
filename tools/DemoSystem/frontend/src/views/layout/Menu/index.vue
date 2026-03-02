<template>
  <el-menu
      :default-active="activeMenu"
      class="menu"
      mode="horizontal"
      unique-opened
      router
  >
    <el-menu-item class="logo-item">
      <img
          style="height: 80%;"
          src="@/assets/img/seed.png"
          alt="logo"
      />
    </el-menu-item>
    <div class="right-items">
      <component
          :is="'MenuAside'"
          v-for="item in menuList"
          :key="item.path"
          :menu-item="item"
      />
      <!--      <MenuAside-->
      <!--          v-for="item in menuList"-->
      <!--          :key="item.path"-->
      <!--          :menu-item="item"-->
      <!--      />-->
    </div>
  </el-menu>
</template>

<script lang="ts">
import MenuAside from './MenuAside/index.vue';

export default {
  components: {
    MenuAside,
  }
}
</script>

<script setup lang="ts">
import {useRoute} from "vue-router"

interface Props {
  menuList: any[];
}

const props = withDefaults(defineProps<Props>(), {});
const route = useRoute();
const activeMenu = computed(() => route.path)
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