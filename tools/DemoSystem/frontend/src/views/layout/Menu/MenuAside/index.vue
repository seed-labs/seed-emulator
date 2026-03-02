<template>
  <el-menu-item
      v-if="!menuItem.children?.length" :index="menuItem.path"
      :class="{ 'is-active': isActive }"
  >
    <span>{{ menuItem.meta.title }}</span>
  </el-menu-item>
  <el-sub-menu v-else :index="menuItem.path">
    <template #title>
      <span :class="{ 'is-active': isActive }">{{ menuItem.meta.title }}</span>
    </template>
    <MenuAside
        v-for="child in menuItem.children"
        :menu-item="child"
        :key="child.path"
    />
  </el-sub-menu>
</template>

<script lang="ts">

export default {
  name: "MenuAside",
  components: {}
}
</script>

<script setup lang="ts">

import {useRoute} from "vue-router";

interface MenuItem {
  name: string
  path: string
  meta: {
    title: string
  }
  children?: MenuItem[]
}

interface Props {
  menuItem: MenuItem;
}

const props = withDefaults(defineProps<Props>(), {});
const isMenuItemActive = (menuItemPath: string, currentPath: string): boolean => {
  // 精确匹配
  if (menuItemPath === currentPath) {
    return true
  }

  // 父路径匹配（当前路径以菜单路径开头）
  if (currentPath.startsWith(menuItemPath + '/')) {
    return true
  }

  // 处理末尾斜杠的情况
  const normalizedMenuItemPath = menuItemPath.replace(/\/$/, '')
  const normalizedCurrentPath = currentPath.replace(/\/$/, '')

  return normalizedMenuItemPath === normalizedCurrentPath;
}
const route = useRoute();
const isActive = computed(() => {
  return isMenuItemActive(props.menuItem.path, route.path)
})
</script>

<style scoped>
.is-active {
  color: var(--el-color-primary);
}
</style>